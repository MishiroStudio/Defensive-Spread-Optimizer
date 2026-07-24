import json
import requests


pokemon_list = []

for dex in range(1, 1026):
    print("Loading Pokémon", dex)

    url = f"https://pokeapi.co/api/v2/pokemon/{dex}"
    response = requests.get(url)

    if response.status_code != 200:
        print("Could not load Pokémon", dex)
        continue

    data = response.json()

    base_stats = {}

    for stat in data["stats"]:
        stat_name = stat["stat"]["name"]
        base_stat = stat["base_stat"]

        base_stats[stat_name] = base_stat

    species_url = f"https://pokeapi.co/api/v2/pokemon-species/{dex}"
    species_response = requests.get(species_url)

    if species_response.status_code != 200:
        german_name = ""
    else:
        species_data = species_response.json()

        german_name = ""

        for name in species_data["names"]:
            if name["language"]["name"] == "de":
                german_name = name["name"]
                break

    pokemon = {
        "dex": data["id"],
        "name_en": data["name"].capitalize(),
        "name_de": german_name,

        "base_hp": base_stats["hp"],
        "base_atk": base_stats["attack"],
        "base_def": base_stats["defense"],
        "base_spa": base_stats["special-attack"],
        "base_spd": base_stats["special-defense"],
        "base_spe": base_stats["speed"]
    }

    pokemon_list.append(pokemon)

with open("../data/pokemon.json", "w", encoding="utf-8") as file:
    json.dump(pokemon_list, file, ensure_ascii=False, indent=4)

print("Done!")