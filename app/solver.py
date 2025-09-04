import time

import highspy
import nextmv

from app.input import Input, Slot
from app.output import Assignment, Group, Match, Output


def solve(input: Input, groups: list[Group]) -> Output:
    """
    Solve the tennis scheduling problem.

    Parameters:
    ----------
    input : Input
        The input data for the problem.

    Returns
    -------
    Output
        The output data for the problem.
    """

    start_time = time.time()

    nextmv.log(f"Processing {len(input.players_by_id)} players.")

    solver = highspy.Highs()
    solver.setOptionValue("time_limit", input.options.duration)
    solver.setOptionValue("threads", input.options.threads)

    assignment_variables = __variables(
        input=input,
        groups=groups,
        solver=solver,
    )

    __constraints(
        input=input,
        groups=groups,
        assignment_variables=assignment_variables,
        solver=solver,
    )

    objective_function = __objective_function(
        input=input,
        groups=groups,
        assignment_variables=assignment_variables,
    )
    nextmv.log("Starting solver optimization.")
    _ = solver.maximize(objective_function)
    nextmv.log("Finished solver optimization.")

    # Build the assignments.
    assignments = __assignments(
        input=input,
        groups=groups,
        assignment_variables=assignment_variables,
        solver=solver,
    )
    nextmv.log(f"Created {len(assignments)} assignments.")

    statistics = nextmv.Statistics(
        run=nextmv.RunStatistics(duration=time.time() - start_time),
        result=nextmv.ResultStatistics(
            value=solver.getInfo().objective_function_value,
            custom={
                "status": solver.modelStatusToString(solver.getModelStatus()),
                "variables": solver.numVariables,
                "constraints": solver.numConstrs,
            },
        ),
    )

    return Output(
        groups=groups,
        options=input.options,
        assignments=assignments,
        statistics=statistics,
        input=input,
    )


def __variables(input: Input, groups: list[Group], solver: highspy.Highs) -> dict[str, any]:
    """Create the decision variables for the problem.

    Parameters
    ----------
    groups : list[Group]
        The groups.
    slots : list[Slot]
        The slots.
    time_block_ranking : dict[str, int]
        The time block ranking.
    solver : highspy.Highs
        The solver object.

    Returns
    -------
    dict[str, highspy.HighsVar]
        The assignment variables.
    """

    variables = {}
    for group in groups:
        for match in group.matches:
            for slot in input.slots:
                var_name = __assign_var_name(match, slot)
                variable = solver.addVariable(0, 1, type=highspy.HighsVarType.kInteger, name=var_name)
                variables[var_name] = variable

    return variables


def __constraints(  # noqa: C901
    input: Input,
    groups: list[Group],
    assignment_variables: dict[str, any],
    solver: highspy.Highs,
) -> None:
    """Create the constraints for the problem.

    Parameters
    ----------
    groups : list[Group]
        The groups.
    slots : list[Slot]
        The slots.
    assignment_variables : dict[str, highspy.HighsVar]
        The assignment variables.
    time_block_ranking : dict[str, int]
        The time block ranking.
    solver : highspy.Highs
        The solver object.
    """

    # Each match must be scheduled exactly once.
    for group in groups:
        for match in group.matches:
            slot_sum = sum(assignment_variables[__assign_var_name(match, slot)] for slot in input.slots)
            solver.addConstr(slot_sum == 1, f"match-{match.match_id}")

    # At most one match can be scheduled in each slot.
    for slot in input.slots:
        slot_sum = sum(
            assignment_variables[__assign_var_name(match, slot)] for group in groups for match in group.matches
        )
        solver.addConstr(slot_sum <= 1, f"slot-{slot.name()}")

    # Matches are assigned to the slots that their division allows.
    for group in groups:
        division = group.division
        allowed_time_blocks = input.division_availability[division]
        for match in group.matches:
            for slot in input.slots:
                if slot.time_block_id in allowed_time_blocks:
                    continue

                var = assignment_variables[__assign_var_name(match, slot)]
                solver.addConstr(var == 0, f"availability-{match.match_id}-{slot.name()}")

    # Each player can only play one match at a time.
    for group in groups:
        for player in group.players:
            matches = group.matches_by_player[player.player_id]
            for time_block_id, block_slots in input.slots_by_time_block.items():
                slot_sum = 0
                for match in matches:
                    for slot in block_slots:
                        var = assignment_variables[__assign_var_name(match, slot)]
                        slot_sum += var

                solver.addConstr(slot_sum <= 1, f"player-{player.player_id}-{time_block_id}")

    # Each player has demands for specific time blocks. They cannot be booked
    # outside of those.
    for group in groups:
        for player in group.players:
            time_block_demands = input.time_block_demands_by_player.get(player.player_id)
            has_demands = time_block_demands is not None
            if not has_demands:
                continue

            matches = group.matches_by_player[player.player_id]
            for slot in input.slots:
                if slot.time_block_id not in time_block_demands:
                    for match in matches:
                        var = assignment_variables[__assign_var_name(match, slot)]
                        solver.addConstr(var == 0, f"demand-{match.match_id}-{slot.name()}-{player.player_id}")

    # Scheduling 3 back-to-back matches for the same player is not allowed.
    time_block_keys = list(input.slots_by_time_block.keys())
    for group in groups:
        for player in group.players:
            for i in range(len(time_block_keys) - 2):
                time_block_id_1 = time_block_keys[i]
                ranking_1 = input.time_block_ranking[time_block_id_1]

                time_block_id_2 = time_block_keys[i + 1]
                ranking_2 = input.time_block_ranking[time_block_id_2]

                time_block_id_3 = time_block_keys[i + 2]
                ranking_3 = input.time_block_ranking[time_block_id_3]

                # Only if the three slots are batched together we need
                # the penalty.
                if (ranking_2 - ranking_1 != 1) or (ranking_3 - ranking_2 != 1) and (ranking_3 - ranking_1 != 2):
                    continue

                slot_1_sum = 0
                for slot in input.slots_by_time_block[time_block_id_1]:
                    for match in group.matches_by_player[player.player_id]:
                        var = assignment_variables[__assign_var_name(match, slot)]
                        slot_1_sum += var

                slot_1_var = solver.addVariable(
                    0,
                    1,
                    type=highspy.HighsVarType.kInteger,
                    name=f"{player.player_id}-{time_block_id_1}-{slot.name()}",
                )
                solver.addConstr(slot_1_var <= slot_1_sum)
                solver.addConstr(slot_1_var * 999 >= slot_1_sum)

                slot_2_sum = 0
                for slot in input.slots_by_time_block[time_block_id_2]:
                    for match in group.matches_by_player[player.player_id]:
                        var = assignment_variables[__assign_var_name(match, slot)]
                        slot_2_sum += var

                slot_2_var = solver.addVariable(
                    0,
                    1,
                    type=highspy.HighsVarType.kInteger,
                    name=f"{player.player_id}-{time_block_id_2}-{slot.name()}",
                )
                solver.addConstr(slot_2_var <= slot_2_sum)
                solver.addConstr(slot_2_var * 999 >= slot_2_sum)

                slot_3_sum = 0
                for slot in input.slots_by_time_block[time_block_id_3]:
                    for match in group.matches_by_player[player.player_id]:
                        var = assignment_variables[__assign_var_name(match, slot)]
                        slot_3_sum += var

                slot_3_var = solver.addVariable(
                    0,
                    1,
                    type=highspy.HighsVarType.kInteger,
                    name=f"{player.player_id}-{time_block_id_3}-{slot.name()}",
                )
                solver.addConstr(slot_3_var <= slot_3_sum)
                solver.addConstr(slot_3_var * 999 >= slot_3_sum)

                solver.addConstr(slot_1_var + slot_2_var + slot_3_var <= 2, f"back-to-back-{match.match_id}")


def __objective_function(  # noqa: C901
    input: Input,
    groups: list[Group],
    assignment_variables: dict[str, any],
) -> any:
    """Create the objective function for the problem.

    Parameters
    ----------
    groups : list[Group]
        The groups.
    slots : list[Slot]
        The slots.
    assignment_variables : dict[str, highspy.HighsVar]
        The assignment variables.
    time_block_ranking : dict[str, int]
        The time block ranking.
    """

    value = 0

    # Players have a preference for certain slots.
    for slot in input.slots:
        for group in groups:
            for match in group.matches:
                preferences = 0
                for preference in match.player1.preferences:
                    if preference.time_block_id == slot.time_block_id:
                        preferences += preference.preference

                for preference in match.player2.preferences:
                    if preference.time_block_id == slot.time_block_id:
                        preferences += preference.preference
                        break

                var = assignment_variables[__assign_var_name(match, slot)]
                value += preferences * var

    # Using dummy slots is not preferred.
    for slot in input.slots:
        if not slot.is_dummy:
            continue

        for group in groups:
            for match in group.matches:
                var = assignment_variables[__assign_var_name(match, slot)]
                value += -1 * input.options.dummy_penalty * var

    # Scheduling back-to-back matches for the same player is not preferred.
    for group in groups:
        for player in group.players:
            for match in group.matches_by_player[player.player_id]:
                for i in range(len(input.slots) - 1):
                    slot_1 = input.slots[i]
                    ranking_1 = input.time_block_ranking[slot_1.time_block_id]
                    var_1 = assignment_variables[__assign_var_name(match, slot_1)]

                    for j in range(i + 1, len(input.slots)):
                        slot_2 = input.slots[j]
                        ranking_2 = input.time_block_ranking[slot_2.time_block_id]
                        var_2 = assignment_variables[__assign_var_name(match, slot_2)]

                        # Only if the diff is exactly 1 it means that they are
                        # back-to-back and we need the penalty.
                        if ranking_2 - ranking_1 != 1:
                            continue

                        penalty = input.options.back_to_back_penalty * (var_1 + var_2 - 1)
                        value += -1 * penalty

    return value


def __assignments(
    input: Input,
    groups: list[Group],
    assignment_variables: dict[str, any],
    solver: highspy.Highs,
) -> list[Assignment]:
    """Create the assignments from the variables.

    Parameters
    ----------
    groups : list[Group]
        The groups.
    slots : list[Slot]
        The slots.
    variables : dict[str, highspy.HighsVar]
        The variables.
    solver : highspy.Highs
        The solver object.

    Returns
    -------
    list[Assignment]
        The assignments.
    """

    assignments = []
    for group in groups:
        for match in group.matches:
            for slot in input.slots:
                var = assignment_variables[__assign_var_name(match, slot)]
                if solver.val(var) > 0.9:
                    assignment = Assignment(match=match, slot=slot)
                    assignments.append(assignment)

    return assignments


def __assign_var_name(match: Match, slot: Slot) -> str:
    """Create the variable name for a match and slot.

    Parameters
    ----------
    match : Match
        The match.
    slot : Slot
        The slot.

    Returns
    -------
    str
        The variable name.
    """

    return f"{match.match_id}-{slot.name()}"
