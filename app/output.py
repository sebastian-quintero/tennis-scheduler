import copy
from dataclasses import dataclass

import nextmv
import pandas as pd

from app.input import Input, Player, Slot


@dataclass
class Match:
    """A class that represents a match between two players"""

    match_id: str
    """str: The match's unique identifier."""
    player1: Player
    """Player: The first player in the match."""
    player2: Player
    """Player: The second player in the match."""
    group_id: str
    """str: The group's unique identifier to which the match belongs to."""
    division: str
    """str: The division of the match."""


@dataclass
class Group:
    """A class that represents a group of players"""

    group_id: str
    """str: The group's unique identifier."""
    division: str
    """str: The division of the group"""
    players: list[Player]
    """list[Player]: The players in the group."""
    matches: list[Match] | None = None
    """list[Match]: The matches in the group."""
    matches_by_player: dict[str, list[Match]] | None = None
    """dict[str, list[Match]]: The matches grouped by player."""


@dataclass
class Assignment:
    """A class that represents the assignment of a tennis match to a slot."""

    match: Match
    """Match: The match that was assigned."""
    slot: Slot
    """Slot: The slot to which the match was assigned."""


@dataclass
class Output:
    """A class that represents the output of the tennis scheduling problem."""

    options: nextmv.Options | None = None
    """nextmv.Options: The options used to generate the output."""
    groups: list[Group] | None = None
    """list[Group]: The list of groups that were created for the players."""
    assignments: list[Assignment] | None = None
    """list[Assignment]: The list of assignments of matches to slots."""
    statistics: nextmv.Statistics | None = None
    """nextmv.Statistics: The statistics of the optimization run."""
    input: Input | None = None
    """Input: The input object used to generate the output."""
    parsed_preferences: list[dict[str, any]] | None = None
    """list[dict[str, any]]: The parsed preferences for the players."""

    def to_excel(self) -> None:
        """Write the groups and their matches to an Excel file."""

        with pd.ExcelWriter(self.options.output, engine="openpyxl") as writer:
            if self.parsed_preferences is not None:
                df = pd.DataFrame(self.parsed_preferences)
                df.to_excel(writer, sheet_name="parsed_preferences", index=False)
                return

            groups_df = self.__groups_dataframe(self.groups)
            groups_df.to_excel(writer, sheet_name="groups", index=False)

            assignments_dfs = self.__assignments_dataframe(self.assignments, self.input)
            for sheet_name, assignments_df in assignments_dfs.items():
                assignments_df.to_excel(writer, sheet_name=sheet_name, index=False)

    @staticmethod
    def __assignments_dataframe(assignments: list[Assignment], input: Input) -> dict[str, pd.DataFrame]:  # noqa: C901
        """
        Convert the list of matches to a DataFrame.

        Parameters
        ----------
        groups : list[Group]
            The list of Group objects.

        Returns
        -------
        dict[str, pd.DataFrame]
            The DataFrames containing the match information.
        """

        data = []
        assignments = [] if assignments is None else assignments
        for assignment in assignments:
            time_block = assignment.slot.time_block_id

            preferred_slot = ""
            for preference in assignment.match.player1.preferences:
                if preference.time_block_id != time_block:
                    continue

                if preference.preference > 0:
                    preferred_slot += "✅|"
                elif preference.preference == 0:
                    preferred_slot += "➖|"
                elif preference.preference < 0:
                    preferred_slot += "❌|"

            for preference in assignment.match.player2.preferences:
                if preference.time_block_id != time_block:
                    continue

                if preference.preference > 0:
                    preferred_slot += "|✅"
                elif preference.preference == 0:
                    preferred_slot += "|➖"
                elif preference.preference < 0:
                    preferred_slot += "|❌"

            data_entry = {
                "division_id": assignment.match.division,
                "group_id": assignment.match.group_id,
                "match_id": assignment.match.match_id,
                "player1": assignment.match.player1.name,
                "player2": assignment.match.player2.name,
                "court_id": assignment.slot.court_id,
                "time_block_id": time_block,
                "time_block_ranking": input.time_block_ranking[time_block],
                "preferred_slot": preferred_slot,
                "dummy_slot": "**" if assignment.slot.is_dummy else "",
            }
            data.append(data_entry)

        by_group = sorted(copy.deepcopy(data), key=lambda x: (x["division_id"], x["group_id"], x["match_id"]))
        by_time_block = sorted(copy.deepcopy(data), key=lambda x: (x["time_block_ranking"], x["court_id"]))

        return {
            "matches_by_group": pd.DataFrame(by_group),
            "matches_by_time_block": pd.DataFrame(by_time_block),
        }

    @staticmethod
    def __groups_dataframe(groups: list[Group]) -> pd.DataFrame:
        """
        Convert a list of Group objects to a DataFrame.

        Parameters
        ----------
        groups : list[Group]
            The list of Group objects.

        Returns
        -------
        pd.DataFrame
            The DataFrame containing the group information.
        """

        data = []
        for group in groups:
            for player in group.players:
                data.append(
                    {
                        "division_id": group.division,
                        "group_id": group.group_id,
                        "player": player.name,
                        "seed": "**" if player.seed else "",
                    }
                )

        return pd.DataFrame(data)
