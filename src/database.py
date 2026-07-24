import json
import sys
from pathlib import Path


if getattr(sys, "frozen", False):
    BASE_DIR = Path(__file__).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"


def load_pokemon():
    file_path = DATA_DIR / "pokemon.json"

    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def get_pokemon(name):
    pokemon_list = load_pokemon()
    name = name.lower()

    for pokemon in pokemon_list:
        if pokemon["name_en"].lower() == name:
            return pokemon

        if pokemon["name_de"].lower() == name:
            return pokemon

    return None