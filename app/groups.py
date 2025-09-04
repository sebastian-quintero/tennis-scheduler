import math
import random
from collections import defaultdict

import nextmv
import pandas as pd

from app.input import Input, Player
from app.output import Group, Match


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
        random.shuffle(unseeded_players)

        group_index = 0
        for player in unseeded_players:
            group = division_groups[group_index]
            group.players.append(player)
            group_index = (group_index + 1) % len(division_groups)

        groups.extend(division_groups)

    for group in groups:
        matches, matches_by_player = __player_matches(group)
        group.matches = matches
        group.matches_by_player = matches_by_player

    nextmv.log(f"Created {len(groups)} groups.")

    total_matches = sum(len(group.matches) for group in groups)

    nextmv.log(f"Created {total_matches} matches.")

    return groups


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
