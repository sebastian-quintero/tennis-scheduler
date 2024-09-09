from app.input import Input

TIME_BLOCK_TRANSLATION = {
    "Preferencia de horarios [Sábado 07/09/24 6:00 a.m. - 11:59 a.m.]": [
        "Sábado 07/09, 6:00 a.m. - 7:15 a.m.",
        "Sábado 07/09, 7:15 a.m. - 8:30 a.m.",
        "Sábado 07/09, 8:30 a.m. - 9:45 a.m.",
        "Sábado 07/09, 9:45 a.m. - 11:00 a.m.",
    ],
    "Preferencia de horarios [Sábado 07/09/24 12:00 m. - 04:59 p.m.]": [
        "Sábado 07/09, 12:15 p.m. - 1:30 p.m.",
        "Sábado 07/09, 1:30 p.m. - 2:45 p.m.",
        "Sábado 07/09, 2:45 p.m. - 4:00 p.m.",
        "Sábado 07/09, 4:00 p.m. - 5:15 p.m.",
    ],
    "Preferencia de horarios [Domingo 08/09/24 6:00 a.m. - 11:59 a.m.]": [
        "Domingo 08/09, 6:00 a.m. - 7:15 a.m.",
        "Domingo 08/09, 7:15 a.m. - 8:30 a.m.",
        "Domingo 08/09, 8:30 a.m. - 9:45 a.m.",
        "Domingo 08/09, 9:45 a.m. - 11:00 a.m.",
    ],
    "Preferencia de horarios [Domingo 08/09/24 12:00 m. - 04:59 p.m.]": [
        "Domingo 08/09, 12:15 p.m. - 1:30 p.m.",
        "Domingo 08/09, 1:30 p.m. - 2:45 p.m.",
        "Domingo 08/09, 2:45 p.m. - 4:00 p.m.",
        "Domingo 08/09, 4:00 p.m. - 5:15 p.m.",
    ],
}
PREFERENCE_TRANSLATION = {
    "¡Me gustaría!": 2,
    "Me es indiferente": 0,
    "¡No me gustaría!": -1,
}


def parse_preferences(input: Input) -> list[dict[str, any]]:
    """Parse the raw preferences from the input data."""

    preferences = []
    for raw_preference in input.raw_preferences:
        player_id = raw_preference["player_id"]
        for column_name, value in raw_preference.items():
            if column_name in ["name", "player_id"]:
                continue

            for time_block in TIME_BLOCK_TRANSLATION[column_name]:
                preference = {
                    "player_id": player_id,
                    "time_block_id": time_block,
                    "preference": PREFERENCE_TRANSLATION[value],
                }
                preferences.append(preference)

    return preferences
