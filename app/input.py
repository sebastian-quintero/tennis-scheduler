from collections import defaultdict
from dataclasses import dataclass, field

import nextmv
import pandas as pd


@dataclass
class Preference:
    """A class to represent a player's preference for a slot."""

    player_id: str
    """str: The player's unique identifier."""
    time_block_id: str
    """str: The schedule's unique identifier."""
    preference: int
    """int: The player's preference for the schedule."""

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "Preference":
        """Create a Preference object from a dictionary.

        Parameters
        ----------
        data : dict[str, str]
            The dictionary containing the preference information.

        Returns
        -------
        Preference
            The Preference object.
        """

        return Preference(
            player_id=str(data["player_id"]),
            time_block_id=str(data["time_block_id"]),
            preference=int(data["preference"]),
        )


@dataclass
class Player:
    """A class to represent a player in the tennis scheduling problem."""

    player_id: str
    """str: The player's unique identifier."""
    name: str
    """str: The player's name."""
    division: str
    """str: The player's division."""
    ranking: int
    """int: The player's ranking."""

    seed: bool | None = False
    """bool: Whether the player is a seed or not."""
    preferences: list[Preference] | None = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "Player":
        """Create a Player object from a dictionary.

        Parameters
        ----------
        data : dict[str, str]
            The dictionary containing the player information.

        Returns
        -------
        Player
            The Player object.
        """

        return Player(
            player_id=str(data["player_id"]),
            name=data["name"],
            division=str(data["division_id"]),
            ranking=int(data["ranking"]),
        )


@dataclass
class Slot:
    """A class that represents a possible slot for scheduling a match."""

    court_id: str
    """str: The court's unique identifier."""
    time_block_id: str
    """str: The schedule's unique identifier."""
    is_dummy: bool
    """bool: Whether the slot is a dummy slot or not."""

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "Slot":
        """Create a Schedule object from a dictionary.

        Parameters
        ----------
        data : dict[str, str]
            The dictionary containing the schedule information.

        Returns
        -------
        Schedule
            The Schedule object.
        """

        return Slot(
            court_id=str(data["court_id"]),
            time_block_id=str(data["time_block_id"]),
            is_dummy=True if data["is_dummy"] == "yes" else False,
        )

    def name(self) -> str:
        """Return the name of the slot.

        Returns
        -------
        str
            The name of the slot.
        """

        return f"{self.court_id}-{self.time_block_id}"


@dataclass
class Input:
    """A class to represent the complete information for the tennis scheduling
    problem."""

    raw: nextmv.Input
    """nextmv.Input: The raw input object."""
    options: nextmv.Options
    """nextmv.Options: The options used to create the input."""

    players_by_division: dict[str, list[Player]] | None = field(default_factory=dict)
    """The players grouped by division."""
    players_by_id: dict[str, Player] | None = field(default_factory=dict)
    """The players grouped by their unique identifier."""
    slots: list[Slot] | None = field(default_factory=list)
    """The available slots for the matches."""
    division_availability: dict[str, list[str]] | None = field(default_factory=dict)
    """The availability of the schedules for each division."""
    time_block_ranking: dict[str, int] | None = field(default_factory=dict)
    """The ranking of the time blocks."""
    slots_by_time_block: dict[str, list[Slot]] | None = field(default_factory=list)
    """The slots grouped by time block."""
    raw_preferences: list[dict[str, str]] | None = field(default_factory=list)
    """The raw preferences data."""
    time_block_demands_by_player: dict[str, list[str]] | None = field(default_factory=dict)
    """The time block demands by player."""

    @classmethod
    def from_excel(cls, options: nextmv.Options) -> "Input":
        """Create an Input object from an Excel file.

        Parameters
        ----------
        options : nextmv.Options
            The options object containing information to load the file.

        Returns
        -------
        Input
            The Input object.
        """

        all_sheets = pd.read_excel(options.input, sheet_name=None)

        data = {}
        for sheet_name, df in all_sheets.items():
            data[sheet_name] = df.to_dict(orient="records")

        input = nextmv.Input(
            data=data,
            input_format=nextmv.InputFormat.CSV_ARCHIVE,
            options=options,
        )

        if options.process_time_blocks:
            return cls(
                raw=input,
                options=options,
                raw_preferences=input.data["raw_preferences"],
            )

        players_by_division = defaultdict(list)
        players_by_id = {}
        for input_player in input.data["players"]:
            player = Player.from_dict(input_player)
            players_by_division[player.division].append(player)
            players_by_id[player.player_id] = player

        slots = []
        slots_by_time_block = defaultdict(list)
        for slot_dict in input.data["slots"]:
            slot = Slot.from_dict(slot_dict)
            slots.append(slot)
            slots_by_time_block[slot.time_block_id].append(slot)

        for input_preference in input.data["player_preferences"]:
            preference = Preference.from_dict(input_preference)
            player = players_by_id[preference.player_id]
            player.preferences.append(preference)

        division_availability = defaultdict(list)
        for availability in input.data["division_availability"]:
            division = str(availability["division_id"])
            time_block_id = str(availability["time_block_id"])
            division_availability[division].append(time_block_id)

        time_block_ranking = {}
        for row in input.data["time_block_ranking"]:
            time_block_id = str(row["time_block_id"])
            ranking = int(row["ranking"])
            time_block_ranking[time_block_id] = ranking

        time_block_demands = defaultdict(list)
        for demand in input.data["player_demands"]:
            player_id = str(demand["player_id"])
            time_block_id = str(demand["time_block_id"])
            time_block_demands[player_id].append(time_block_id)

        return cls(
            raw=input,
            options=options,
            players_by_division=dict(players_by_division),
            players_by_id=players_by_id,
            slots=slots,
            division_availability=dict(division_availability),
            time_block_ranking=dict(time_block_ranking),
            slots_by_time_block=dict(slots_by_time_block),
            raw_preferences=input.data["raw_preferences"],
            time_block_demands_by_player=dict(time_block_demands),
        )
