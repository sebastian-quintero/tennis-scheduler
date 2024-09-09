import json

import nextmv

from app.input import Input
from app.output import Output
from app.preferences import parse_preferences
from app.solver import solve


def main() -> None:
    """Entry point for the program."""

    options = nextmv.Options(
        nextmv.Parameter("input", str, "tennis.xlsx", "Path to the input Excel file.", required=False),
        nextmv.Parameter("group_size", int, 4, "The maximum number of players in each group.", required=False),
        nextmv.Parameter("output", str, "tennis_schedules.xlsx", "Path to the output Excel file.", required=False),
        nextmv.Parameter("duration", int, 30, "Max runtime duration (in seconds).", required=False),
        nextmv.Parameter("threads", int, 10, "NUmber of threads used by the solver.", required=False),
        nextmv.Parameter("dummy_penalty", int, 1, "Penalty for assigning a match to a dummy slot.", required=False),
        nextmv.Parameter(
            name="back_to_back_penalty",
            param_type=int,
            default=1,
            description="Penalty for assigning a match to a back-to-back slot.",
            required=False,
        ),
        nextmv.Parameter("process_time_blocks", bool, False, "Process the time blocks.", required=False),
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

    output = solve(input)

    nextmv.log(f"Writing output to file {options.output}.")
    output.to_excel()

    if output.statistics is not None:
        print(json.dumps(output.statistics.to_dict(), indent=2))


if __name__ == "__main__":
    main()
