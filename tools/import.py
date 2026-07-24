import json
from pathlib import Path

import requests


API_BASE_URL = "https://pokeapi.co/api/v2"

OUTPUT_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "pokemon.json"
)

session = requests.Session()
session.headers.update({
    "User-Agent": "Defensive-Spread-Optimizer"
})


def get_json(url: str) -> dict:
    """Load JSON data from PokéAPI."""
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def get_localized_name(entries: list[dict], language: str) -> str:
    """Return a localized name from a PokéAPI names list."""
    for entry in entries:
        if entry["language"]["name"] == language:
            return entry["name"]

    return ""


def get_base_stats(pokemon_data: dict) -> dict[str, int]:
    """Convert the PokéAPI stats list into a dictionary."""
    return {
        stat["stat"]["name"]: stat["base_stat"]
        for stat in pokemon_data["stats"]
    }


def get_stat_signature(base_stats: dict[str, int]) -> tuple[int, ...]:
    """Create a comparable signature containing all six base stats."""
    return (
        base_stats["hp"],
        base_stats["attack"],
        base_stats["defense"],
        base_stats["special-attack"],
        base_stats["special-defense"],
        base_stats["speed"],
    )


def get_api_form_suffix(
    species_api_name: str,
    pokemon_api_name: str,
) -> str:
    """Extract the form suffix from a Pokémon API name."""
    prefix = f"{species_api_name}-"

    if pokemon_api_name.startswith(prefix):
        return pokemon_api_name[len(prefix):]

    return ""


# Einheitliche Bezeichnungen für häufige Formen.
# Reihenfolge im Tupel: Englisch, Deutsch
FORM_LABELS = {
    "male": ("Male", "Männlich"),
    "female": ("Female", "Weiblich"),

    "small": ("Small", "Klein"),
    "average": ("Average", "Normal"),
    "large": ("Large", "Groß"),
    "super": ("Super", "Extragroß"),

    "normal": ("Normal", "Normal"),
    "attack": ("Attack", "Angriff"),
    "defense": ("Defense", "Verteidigung"),
    "speed": ("Speed", "Initiative"),

    "mega": ("Mega", "Mega"),
    "mega-x": ("Mega X", "Mega X"),
    "mega-y": ("Mega Y", "Mega Y"),
    "primal": ("Primal", "Proto"),

    "alola": ("Alola", "Alola"),
    "galar": ("Galar", "Galar"),
    "hisui": ("Hisui", "Hisui"),
    "paldea": ("Paldea", "Paldea"),

    "altered": ("Altered", "Wandel"),
    "origin": ("Origin", "Urform"),
    "land": ("Land", "Land"),
    "sky": ("Sky", "Zenit"),

    "standard": ("Standard", "Standard"),
    "zen": ("Zen", "Trance"),
    "galar-standard": ("Galar Standard", "Galar-Standard"),
    "galar-zen": ("Galar Zen", "Galar-Trance"),

    "incarnate": ("Incarnate", "Inkarnation"),
    "therian": ("Therian", "Tiergeist"),

    "black": ("Black", "Schwarz"),
    "white": ("White", "Weiß"),

    "shield": ("Shield", "Schild"),
    "blade": ("Blade", "Klinge"),

    "midday": ("Midday", "Tag"),
    "midnight": ("Midnight", "Nacht"),
    "dusk": ("Dusk", "Zwielicht"),

    "solo": ("Solo", "Einzel"),
    "school": ("School", "Schwarm"),

    "zero": ("Zero", "Alltag"),
    "hero": ("Hero", "Held"),

    "ice": ("Ice Face", "Eisgesicht"),
    "noice": ("Noice Face", "Noice-Gesicht"),

    "amped": ("Amped", "Hoch"),
    "low-key": ("Low Key", "Tief"),

    "full-belly": ("Full Belly", "Vollmagen"),
    "hangry": ("Hangry", "Kohldampf"),

    "single-strike": ("Single Strike", "Fokussierter Stil"),
    "rapid-strike": ("Rapid Strike", "Fließender Stil"),

    "chest": ("Chest", "Truhe"),
    "roaming": ("Roaming", "Wander"),

    "bloodmoon": ("Bloodmoon", "Blutmond"),
    "terastal": ("Terastal", "Terakristall"),
    "stellar": ("Stellar", "Stellar"),
}


def format_api_suffix(suffix: str) -> str:
    """Turn an API suffix into a readable fallback label."""
    return " ".join(
        part.upper() if part in {"x", "y"} else part.capitalize()
        for part in suffix.split("-")
    )


def get_display_names(
    species_data: dict,
    pokemon_data: dict,
    distinguish_form: bool,
) -> tuple[str, str]:
    """
    Build consistent names in the format:

    Species (Form)
    """

    species_name_en = (
        get_localized_name(species_data["names"], "en")
        or species_data["name"].replace("-", " ").title()
    )

    species_name_de = (
        get_localized_name(species_data["names"], "de")
        or species_name_en
    )

    if not distinguish_form:
        return species_name_en, species_name_de

    suffix = get_api_form_suffix(
        species_data["name"],
        pokemon_data["name"],
    )

    # The normal Pokémon entry often has no suffix.
    if not suffix:
        return species_name_en, species_name_de

    predefined_labels = FORM_LABELS.get(suffix)

    if predefined_labels:
        form_name_en, form_name_de = predefined_labels

    else:
        # For unknown future forms, use PokéAPI's form-only names
        # as a fallback, but never its complete form names.
        form_data = {}

        if pokemon_data.get("forms"):
            form_url = pokemon_data["forms"][0]["url"]

            try:
                form_data = get_json(form_url)
            except requests.RequestException as error:
                print(
                    f"  Could not load form name for "
                    f"{pokemon_data['name']}: {error}"
                )

        form_name_en = get_localized_name(
            form_data.get("form_names", []),
            "en",
        )

        form_name_de = get_localized_name(
            form_data.get("form_names", []),
            "de",
        )

        fallback_name = format_api_suffix(suffix)

        form_name_en = form_name_en or fallback_name
        form_name_de = form_name_de or form_name_en

    return (
        f"{species_name_en} ({form_name_en})",
        f"{species_name_de} ({form_name_de})",
    )


pokemon_list = []

# This loads the current species list automatically.
species_index = get_json(
    f"{API_BASE_URL}/pokemon-species"
    f"?limit=10000&offset=0"
)

species_resources = species_index["results"]
species_total = len(species_resources)

for position, species_resource in enumerate(
    species_resources,
    start=1,
):
    print(
        f"Loading species {position}/{species_total}: "
        f"{species_resource['name']}"
    )

    try:
        species_data = get_json(species_resource["url"])
    except requests.RequestException as error:
        print(
            f"Could not load species "
            f"{species_resource['name']}: {error}"
        )
        continue

    loaded_varieties = []

    # Load every gameplay-relevant variety belonging to the species.
    for variety in species_data["varieties"]:
        pokemon_resource = variety["pokemon"]

        try:
            pokemon_data = get_json(pokemon_resource["url"])
        except requests.RequestException as error:
            print(
                f"  Could not load variety "
                f"{pokemon_resource['name']}: {error}"
            )
            continue

        base_stats = get_base_stats(pokemon_data)

        loaded_varieties.append({
            "is_default": variety["is_default"],
            "pokemon_data": pokemon_data,
            "base_stats": base_stats,
            "signature": get_stat_signature(base_stats),
        })

    default_variety = next(
        (
            variety
            for variety in loaded_varieties
            if variety["is_default"]
        ),
        None,
    )

    if default_variety is None:
        print("  No default variety found.")
        continue

    default_signature = default_variety["signature"]

    # Keep the default variety and every variety with different stats.
    relevant_varieties = [
        variety
        for variety in loaded_varieties
        if (
            variety["is_default"]
            or variety["signature"] != default_signature
        )
    ]

    distinguish_form = len(relevant_varieties) > 1

    for variety in relevant_varieties:
        pokemon_data = variety["pokemon_data"]
        base_stats = variety["base_stats"]

        name_en, name_de = get_display_names(
            species_data,
            pokemon_data,
            distinguish_form,
        )

        pokemon = {
            # National Pokédex number shared by all forms.
            "dex": species_data["id"],

            # Unique PokéAPI identifier for this particular variety.
            "pokemon_id": pokemon_data["id"],
            "api_name": pokemon_data["name"],

            "name_en": name_en,
            "name_de": name_de,

            "base_hp": base_stats["hp"],
            "base_atk": base_stats["attack"],
            "base_def": base_stats["defense"],
            "base_spa": base_stats["special-attack"],
            "base_spd": base_stats["special-defense"],
            "base_spe": base_stats["speed"],
        }

        pokemon_list.append(pokemon)

        if distinguish_form:
            print(f"  Added: {name_de}")


pokemon_list.sort(
    key=lambda pokemon: (
        pokemon["dex"],
        pokemon["pokemon_id"],
    )
)

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

with OUTPUT_FILE.open(
    "w",
    encoding="utf-8",
) as file:
    json.dump(
        pokemon_list,
        file,
        ensure_ascii=False,
        indent=4,
    )

print()
print(f"Done! Imported {len(pokemon_list)} entries.")
print(f"Saved to: {OUTPUT_FILE}")