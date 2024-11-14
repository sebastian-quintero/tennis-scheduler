from app.input import Input

TIME_BLOCK_TRANSLATION = {
    "PREFERENCIA DE HORARIOS [Sábado 16/11/24 6:00 a.m. - 9:59 a.m.]": [
        "Sábado 16/11, 6:00 a.m. - 7:15 a.m.",
        "Sábado 16/11, 7:15 a.m. - 8:30 a.m.",
        "Sábado 16/11, 8:30 a.m. - 9:45 a.m.",
    ],
    "PREFERENCIA DE HORARIOS [Sábado 16/11/24 10:00 a.m. - 11:59 a.m.]": [
        "Sábado 16/11, 9:45 a.m. - 11:00 a.m.",
        "Sábado 16/11, 11:00 a.m. - 12:15 p.m.",
    ],
    "PREFERENCIA DE HORARIOS [Sábado 16/11/24 12:00 m - 4:59 p.m.]": [
        "Sábado 16/11, 12:15 p.m. - 1:30 p.m.",
        "Sábado 16/11, 1:30 p.m. - 2:45 p.m.",
        "Sábado 16/11, 2:45 p.m. - 4:00 p.m.",
        "Sábado 16/11, 4:00 p.m. - 5:15 p.m.",
    ],
    "PREFERENCIA DE HORARIOS [Domingo 17/11/24 6:00 a.m. - 9:59 a.m.]": [
        "Domingo 17/11, 6:00 a.m. - 7:15 a.m.",
        "Domingo 17/11, 7:15 a.m. - 8:30 a.m.",
        "Domingo 17/11, 8:30 a.m. - 9:45 a.m.",
    ],
    "PREFERENCIA DE HORARIOS [Domingo 17/11/24 10:00 a.m. - 11:59 a.m.]": [
        "Domingo 17/11, 9:45 a.m. - 11:00 a.m.",
        "Domingo 17/11, 11:00 a.m. - 12:15 p.m.",
    ],
    "PREFERENCIA DE HORARIOS [Domingo 17/11/24 12:00 m - 4:59 p.m.]": [
        "Domingo 17/11, 12:15 p.m. - 1:30 p.m.",
        "Domingo 17/11, 1:30 p.m. - 2:45 p.m.",
        "Domingo 17/11, 2:45 p.m. - 4:00 p.m.",
        "Domingo 17/11, 4:00 p.m. - 5:15 p.m.",
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
                translation_value = PREFERENCE_TRANSLATION.get(value)
                if translation_value is None:
                    translation_value = 0

                preference = {
                    "player_id": player_id,
                    "time_block_id": time_block,
                    "preference": translation_value,
                }
                preferences.append(preference)

    return preferences
