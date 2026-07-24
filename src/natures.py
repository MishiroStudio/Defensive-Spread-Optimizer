NATURES = {
    "hardy": {
        "id": "hardy",
        "name_en": "Hardy",
        "name_de": "Robust",
        "positive": None,
        "negative": None,
        "attack": 1.0,
        "defense": 1.0,
        "special_attack": 1.0,
        "special_defense": 1.0,
        "speed": 1.0
    },

    "adamant": {
        "id": "adamant",
        "name_en": "Adamant",
        "name_de": "Hart",
        "positive": "attack",
        "negative": "special_attack",
        "attack": 1.1,
        "defense": 1.0,
        "special_attack": 0.9,
        "special_defense": 1.0,
        "speed": 1.0
    },

    "brave": {
        "id": "brave",
        "name_en": "Brave",
        "name_de": "Mutig",
        "positive": "attack",
        "negative": "speed",
        "attack": 1.1,
        "defense": 1.0,
        "special_attack": 1.0,
        "special_defense": 1.0,
        "speed": 0.9
    },

    "modest": {
        "id": "modest",
        "name_en": "Modest",
        "name_de": "Mäßig",
        "positive": "special_attack",
        "negative": "attack",
        "attack": 0.9,
        "defense": 1.0,
        "special_attack": 1.1,
        "special_defense": 1.0,
        "speed": 1.0
    },

    "quiet": {
        "id": "quiet",
        "name_en": "Quiet",
        "name_de": "Ruhig",
        "positive": "special_attack",
        "negative": "speed",
        "attack": 1.0,
        "defense": 1.0,
        "special_attack": 1.1,
        "special_defense": 1.0,
        "speed": 0.9
    },

    "jolly": {
        "id": "jolly",
        "name_en": "Jolly",
        "name_de": "Froh",
        "positive": "speed",
        "negative": "special_attack",
        "attack": 1.0,
        "defense": 1.0,
        "special_attack": 0.9,
        "special_defense": 1.0,
        "speed": 1.1
    },

    "timid": {
        "id": "timid",
        "name_en": "Timid",
        "name_de": "Scheu",
        "positive": "speed",
        "negative": "attack",
        "attack": 0.9,
        "defense": 1.0,
        "special_attack": 1.0,
        "special_defense": 1.0,
        "speed": 1.1
    },

    "bold": {
        "id": "bold",
        "name_en": "Bold",
        "name_de": "Kühn",
        "positive": "defense",
        "negative": "attack",
        "attack": 0.9,
        "defense": 1.1,
        "special_attack": 1.0,
        "special_defense": 1.0,
        "speed": 1.0
    },

    "calm": {
        "id": "calm",
        "name_en": "Calm",
        "name_de": "Still",
        "positive": "special_defense",
        "negative": "attack",
        "attack": 0.9,
        "defense": 1.0,
        "special_attack": 1.0,
        "special_defense": 1.1,
        "speed": 1.0
    },

    "relaxed": {
        "id": "relaxed",
        "name_en": "Relaxed",
        "name_de": "Locker",
        "positive": "defense",
        "negative": "speed",
        "attack": 1.0,
        "defense": 1.1,
        "special_attack": 1.0,
        "special_defense": 1.0,
        "speed": 0.9
    },

    "sassy": {
        "id": "sassy",
        "name_en": "Sassy",
        "name_de": "Frech",
        "positive": "special_defense",
        "negative": "speed",
        "attack": 1.0,
        "defense": 1.0,
        "special_attack": 1.0,
        "special_defense": 1.1,
        "speed": 0.9
    },
    "impish": {
        "id": "impish",
        "name_en": "Impish",
        "name_de": "Pfiffig",
        "positive": "defense",
        "negative": "special_attack",
        "attack": 1.0,
        "defense": 1.1,
        "special_attack": 0.9,
        "special_defense": 1.0,
        "speed": 1.0
    },

    "careful": {
        "id": "careful",
        "name_en": "Careful",
        "name_de": "Sacht",
        "positive": "special_defense",
        "negative": "special_attack",
        "attack": 1.0,
        "defense": 1.0,
        "special_attack": 0.9,
        "special_defense": 1.1,
        "speed": 1.0
    },
}


def get_natures_by_stat_changes(increased_stat, decreased_stat):
    increased_stat = increased_stat.lower().strip()
    decreased_stat = decreased_stat.lower().strip()

    possible_natures = {}

    for nature_id, nature in NATURES.items():
        positive_stat = nature["positive"]
        negative_stat = nature["negative"]

        if increased_stat == "bulk":
            positive_matches = positive_stat in {
                "defense",
                "special_defense"
            }
        else:
            positive_matches = positive_stat == increased_stat

        negative_matches = negative_stat == decreased_stat

        if positive_matches and negative_matches:
            possible_natures[nature_id] = nature

    return possible_natures