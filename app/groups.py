import json
import math
import os
import random
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import nextmv
import pandas as pd

from app.input import Input, Player
from app.output import Group, Match


def resolve_groups(input: Input) -> list[Group]:
    """Resolve the groups: reuse the ones in the groups file, or calculate them.

    If the groups file (option `groups_file`) does not exist, or it was
    generated more than `groups_max_age_hours` ago, the groups are calculated
    and dumped to the file. In every case, the groups are then loaded from the
    file, so re-running the solver uses the same groups.

    Parameters
    ----------
    input : Input
        The input object.

    Returns
    -------
    list[Group]
        The groups.
    """

    path = input.options.groups_file
    max_age = timedelta(hours=input.options.groups_max_age_hours)

    generated_at = __groups_file_generated_at(path)
    if generated_at is None:
        nextmv.log(f"Groups file {path} not found. Calculating groups.")
        __dump_groups(player_groups(input), path)
    elif datetime.now(timezone.utc) - generated_at > max_age:
        nextmv.log(
            f"Groups file {path} was generated at {generated_at.isoformat()}, "
            f"older than {input.options.groups_max_age_hours} hours."
        )
        nextmv.log("Re-calculating groups.")
        __dump_groups(player_groups(input), path)

    return __load_groups_from_json(input, path)


def player_groups(input: Input) -> list[Group]:
    """Group players by division.

    Parameters
    ----------
    input : Input
        The input object.

    Returns
    -------
    list[Group]
        The groups.
    """

    groups = []
    groups_by_id = {}
    for division, players in input.players_by_division.items():
        players = sorted(players, key=lambda x: x.ranking, reverse=False)

        division_groups = []
        num_groups = math.ceil(len(players) / input.options.group_size)

        for i in range(num_groups):
            group_id = f"{division}-{i + 1}"
            seeded = players[i]
            seeded.seed = True
            group = Group(group_id=group_id, division=division, players=[seeded])
            groups_by_id[group_id] = group
            division_groups.append(group)

        unseeded_players = players[num_groups:]
        __assign_unseeded(division, division_groups, unseeded_players, input.separations_by_player)

        groups.extend(division_groups)

    for group in groups:
        matches, matches_by_player = __player_matches(group)
        group.matches = matches
        group.matches_by_player = matches_by_player

    nextmv.log(f"Created {len(groups)} groups.")

    total_matches = sum(len(group.matches) for group in groups)

    nextmv.log(f"Created {total_matches} matches.")

    return groups


def __assign_unseeded(
    division: str,
    division_groups: list[Group],
    unseeded_players: list[Player],
    separations: dict[str, set[str]],
    max_attempts: int = 1000,
) -> None:
    """Randomly distribute unseeded players over the groups of a division,
    keeping group sizes balanced and never placing two players that are
    separated from each other in the same group."""

    # Group capacities are the same ones a round-robin deal would produce.
    capacities = [len(g.players) for g in division_groups]
    for i in range(len(unseeded_players)):
        capacities[i % len(division_groups)] += 1

    seeded = [list(g.players) for g in division_groups]
    for _ in range(max_attempts):
        players = list(unseeded_players)
        random.shuffle(players)
        # Most constrained players first, which makes dead ends rare.
        players.sort(key=lambda p: -len(separations.get(p.player_id, ())))

        assigned = [list(members) for members in seeded]
        ok = True
        for player in players:
            blocked = separations.get(player.player_id, set())
            options = [
                i
                for i, members in enumerate(assigned)
                if len(members) < capacities[i] and not any(m.player_id in blocked for m in members)
            ]
            if not options:
                ok = False
                break
            # Prefer the groups with the most room left, random among ties.
            best = max(capacities[i] - len(assigned[i]) for i in options)
            choice = random.choice([i for i in options if capacities[i] - len(assigned[i]) == best])
            assigned[choice].append(player)

        if ok:
            for group, members in zip(division_groups, assigned):
                group.players = members
            return

    raise ValueError(
        f"Could not place the players of division {division} into groups without breaking the "
        "player_separations constraints. A separation set may be larger than the number of groups."
    )


def load_groups_from_excel(path: str) -> list[Group]:
    """Load groups and matches from an Excel file.

    Parameters
    ----------
    path : str
        Path to the Excel file containing groups and matches data.

    Returns
    -------
    list[Group]
        The loaded groups with players and matches.
    """
    # Read the Excel file
    excel_data = pd.read_excel(path, sheet_name=None)

    if "groups" not in excel_data or "matches" not in excel_data:
        raise ValueError("Excel file must contain both 'groups' and 'matches' sheets")

    groups_df = excel_data["groups"]
    matches_df = excel_data["matches"]

    # Filter out separator rows (those with dashes)
    groups_df = groups_df[~groups_df["division_id"].astype(str).str.contains("-{5,}", na=False)]
    matches_df = matches_df[~matches_df["division_id"].astype(str).str.contains("-{5,}", na=False)]

    # Build groups and players
    groups = []
    groups_by_id = {}
    players_by_name = {}

    # Group the dataframe by group_id to process each group
    grouped_data = groups_df.groupby(["division_id", "group_id"])

    for (division, group_id), group_data in grouped_data:
        players = []
        for _, row in group_data.iterrows():
            player_name = row["player"]
            is_seed = str(row.get("seed", "")).strip() == "**"

            # Create a simple player ID from the name (in the original format)
            player_id = player_name.replace(" ", "_").lower()

            player = Player(
                player_id=player_id,
                name=player_name,
                division=division,
                ranking=0 if is_seed else 1,  # Seed gets ranking 0, others get 1
                seed=is_seed,
            )
            players.append(player)
            players_by_name[player_name] = player

        group = Group(group_id=group_id, division=division, players=players)
        groups.append(group)
        groups_by_id[group_id] = group

    # Process matches and add them to groups
    grouped_matches = matches_df.groupby(["division_id", "group_id"])

    for (division, group_id), match_data in grouped_matches:
        if group_id not in groups_by_id:
            continue

        group = groups_by_id[group_id]
        matches = []
        matches_by_player = defaultdict(list)

        for _, row in match_data.iterrows():
            match_id = row["match_id"]
            player1_name = row["player1"]
            player2_name = row["player2"]

            # Get player objects
            player1 = players_by_name.get(player1_name)
            player2 = players_by_name.get(player2_name)

            if player1 and player2:
                match = Match(match_id=match_id, player1=player1, player2=player2, group_id=group_id, division=division)
                matches.append(match)
                matches_by_player[player1.player_id].append(match)
                matches_by_player[player2.player_id].append(match)

        group.matches = matches
        group.matches_by_player = dict(matches_by_player)

    nextmv.log(f"Loaded {len(groups)} groups from {path}.")

    total_matches = sum(len(group.matches) if group.matches else 0 for group in groups)
    nextmv.log(f"Loaded {total_matches} matches from {path}.")

    return groups


def __groups_file_generated_at(path: str) -> datetime | None:
    """Return when the groups file was generated (in UTC), or None if the
    file does not exist."""

    if not os.path.exists(path):
        return None

    try:
        with open(path, encoding="utf-8") as file:
            generated_at = datetime.fromisoformat(json.load(file)["generated_at"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise ValueError(
            f"Groups file {path} is not valid ({error}). Fix it, or delete it so groups are re-calculated."
        ) from error

    # Timestamps without a timezone are taken as UTC.
    if generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=timezone.utc)

    return generated_at.astimezone(timezone.utc)


def __dump_groups(groups: list[Group], path: str) -> None:
    """Write the groups, their matches, and the UTC generation time to a JSON
    file. The file is written atomically, so a failed write never leaves a
    half-written file behind."""

    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "groups": [
            {
                "group_id": group.group_id,
                "division": group.division,
                "players": [
                    {"player_id": player.player_id, "name": player.name, "seed": bool(player.seed)}
                    for player in group.players
                ],
                "matches": [
                    {
                        "match_id": match.match_id,
                        "player1_id": match.player1.player_id,
                        "player2_id": match.player2.player_id,
                    }
                    for match in group.matches or []
                ],
            }
            for group in groups
        ],
    }

    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)

    nextmv.log(f"Saved {len(groups)} groups to {path}.")


def __load_groups_from_json(input: Input, path: str) -> list[Group]:  # noqa: C901
    """Load groups and matches from a JSON file written by `__dump_groups`.

    Players are matched by `player_id` against the input, so they keep their
    preferences. The file and the input must have exactly the same players.
    """

    with open(path, encoding="utf-8") as file:
        data = json.load(file)

    def mismatch(detail: str) -> ValueError:
        return ValueError(
            f"Groups file {path} does not match the input: {detail}. "
            "Delete it so groups are re-calculated with the current players."
        )

    groups = []
    seen = set()
    for group_data in data["groups"]:
        group_id = group_data["group_id"]
        division = group_data["division"]

        players = []
        for player_data in group_data["players"]:
            player_id = player_data["player_id"]
            player = input.players_by_id.get(player_id)
            if player is None:
                raise mismatch(f"player '{player_id}' is not in the players sheet")
            if player_id in seen:
                raise mismatch(f"player '{player_id}' is in more than one group")
            if player.division != division:
                raise mismatch(f"player '{player_id}' is in division {player.division}, not {division}")

            seen.add(player_id)
            player.seed = bool(player_data.get("seed", False))
            players.append(player)

        group = Group(group_id=group_id, division=division, players=players)

        group_player_ids = {player.player_id for player in players}
        matches = []
        matches_by_player = defaultdict(list)
        for match_data in group_data["matches"]:
            player1_id = match_data["player1_id"]
            player2_id = match_data["player2_id"]
            if player1_id not in group_player_ids or player2_id not in group_player_ids:
                raise mismatch(f"match '{match_data['match_id']}' has a player outside group {group_id}")

            match = Match(
                match_id=match_data["match_id"],
                player1=input.players_by_id[player1_id],
                player2=input.players_by_id[player2_id],
                group_id=group_id,
                division=division,
            )
            matches.append(match)
            matches_by_player[player1_id].append(match)
            matches_by_player[player2_id].append(match)

        group.matches = matches
        group.matches_by_player = dict(matches_by_player)
        groups.append(group)

    missing = sorted(set(input.players_by_id) - seen)
    if missing:
        raise mismatch(f"{len(missing)} player(s) are not in any group, e.g. '{missing[0]}'")

    total_matches = sum(len(group.matches) for group in groups)
    nextmv.log(
        f"Loaded {len(groups)} groups and {total_matches} matches from {path} "
        f"(generated at {data['generated_at']})."
    )

    return groups


def __player_matches(group: Group) -> tuple[list[Match], dict[str, list[Match]]]:
    """Create matches for a group.

    Parameters
    ----------
    group : Group
        The group.

    Returns
    -------
    tuple[list[Match], dict[str, Match]]
        The matches and the matches by player
    """

    matches = []
    counter = 1
    matches_by_player = defaultdict(list)
    for i, player1 in enumerate(group.players):
        for player2 in group.players[i + 1 :]:
            match_id = f"{group.group_id}-{counter}"
            match = Match(
                match_id=match_id,
                player1=player1,
                player2=player2,
                group_id=group.group_id,
                division=group.division,
            )
            matches.append(match)
            counter += 1
            matches_by_player[player1.player_id].append(match)
            matches_by_player[player2.player_id].append(match)

    return matches, dict(matches_by_player)
