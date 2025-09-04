import json

import nextmv

from app.groups import load_groups_from_excel, player_groups
from app.input import Input
from app.output import Output
from app.preferences import parse_preferences
from app.solver import solve


def main() -> None:
    """Entry point for the program."""

    options = nextmv.Options(
        nextmv.Option("input", str, "tennis.xlsx", "Path to the input Excel file.", required=False),
        nextmv.Option("groups_input", str, "tennis.xlsx", "Path to the groups input Excel file.", required=False),
        nextmv.Option("group_size", int, 4, "The maximum number of players in each group.", required=False),
        nextmv.Option("output", str, "tennis_schedules.xlsx", "Path to the output Excel file.", required=False),
        nextmv.Option("duration", int, 30, "Max runtime duration (in seconds).", required=False),
        nextmv.Option("threads", int, 10, "Number of threads used by the solver.", required=False),
        nextmv.Option("dummy_penalty", int, 1, "Penalty for assigning a match to a dummy slot.", required=False),
        nextmv.Option(
            name="back_to_back_penalty",
            option_type=int,
            default=1,
            description="Penalty for assigning a match to a back-to-back slot.",
            required=False,
        ),
        nextmv.Option("process_time_blocks", bool, False, "Process the time blocks.", required=False),
        nextmv.Option("process_groups", bool, False, "Process the groups.", required=False),
    )

    nextmv.log(f"Reading input from file {options.input}.")

    input = Input.from_excel(options)
    nextmv.log("Built input.")

    # Functionality that allows to process the time block preferences from a
    # raw format. This is useful to generate the correct format of player
    # preferences.
    if options.process_time_blocks:
        nextmv.log("Processing time blocks.")
        preferences = parse_preferences(input)
        nextmv.log(f"Processed preferences: {len(preferences)} preferences.")
        output = Output(options=options, parsed_preferences=preferences)
        output.to_excel()
        return

    if options.process_groups:
        nextmv.log("Processing groups.")
        groups = player_groups(input)
        nextmv.log(f"Processed groups: {len(groups)} groups.")
        output = Output(options=options, groups=groups)
        output.to_excel()
        return

    groups = load_groups_from_excel(options.groups_input)

    output = solve(input, groups)
    output.to_excel()

    if output.statistics is not None:
        print(json.dumps(output.statistics.to_dict(), indent=2))


if __name__ == "__main__":
    main()
