import json
from pathlib import Path
import requests


API_BASE_URL = "https://pokeapi.co/api/v2"

PROJECT_DIRECTORY = (
    Path(__file__).resolve().parent.parent
)

OUTPUT_FILE = (
    PROJECT_DIRECTORY
    / "data"
    / "pokemon.json"
)

SPRITE_DIRECTORY = (
    PROJECT_DIRECTORY
    / "assets"
    / "sprites"
    / "home"
)

NORMAL_SPRITE_DIRECTORY = (
    SPRITE_DIRECTORY
    / "normal"
)

SHINY_SPRITE_DIRECTORY = (
    SPRITE_DIRECTORY
    / "shiny"
)

OUTPUT_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "pokemon.json"
)

session = requests.Session()
session.headers.update({
    "User-Agent": "Defensive-Spread-Optimizer"
})


# Einheitliche Bezeichnungen für häufige Formen.
# Reihenfolge: Englisch, Deutsch
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
    "galar-standard": (
        "Galar Standard",
        "Galar-Standard"
    ),
    "galar-zen": (
        "Galar Zen",
        "Galar-Trance"
    ),

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

    "meteor": ("Meteor", "Meteor"),
    "core": ("Core", "Kern"),

    "ice": ("Ice Face", "Eisgesicht"),
    "noice": ("Noice Face", "Noice-Gesicht"),

    "zero": ("Zero", "Alltag"),
    "hero": ("Hero", "Held"),

    "amped": ("Amped", "Hoch"),
    "low-key": ("Low Key", "Tief"),

    "full-belly": ("Full Belly", "Vollmagen"),
    "hangry": ("Hangry", "Kohldampf"),

    "single-strike": (
        "Single Strike",
        "Fokussierter Stil"
    ),
    "rapid-strike": (
        "Rapid Strike",
        "Fließender Stil"
    ),

    "chest": ("Chest", "Truhe"),
    "roaming": ("Roaming", "Wander"),

    "bloodmoon": ("Bloodmoon", "Blutmond"),

    "terastal": ("Terastal", "Terakristall"),
    "stellar": ("Stellar", "Stellar"),
}


def get_json(url: str) -> dict:
    """
    Load JSON data from PokéAPI.
    """
    response = session.get(url, timeout=30)
    response.raise_for_status()

    return response.json()

def download_sprite(
    url: str | None,
    destination: Path
) -> str | None:
    """
    Download the original HOME sprite without resizing it.
    """
    if not url:
        return None

    destination.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    if not destination.exists():
        response = session.get(
            url,
            timeout=30
        )
        response.raise_for_status()

        destination.write_bytes(
            response.content
        )

    return destination.relative_to(
        PROJECT_DIRECTORY
    ).as_posix()


def get_localized_name(
    entries: list[dict],
    language: str
) -> str:
    """
    Return a localized name from a PokéAPI names list.
    """
    for entry in entries:
        if entry["language"]["name"] == language:
            return entry["name"]

    return ""


def get_base_stats(
    pokemon_data: dict
) -> dict[str, int]:
    """
    Convert the PokéAPI stats list into a dictionary.
    """
    return {
        stat["stat"]["name"]: stat["base_stat"]
        for stat in pokemon_data["stats"]
    }


def get_stat_signature(
    base_stats: dict[str, int]
) -> tuple[int, ...]:
    """
    Create a comparable signature of all six base stats.
    """
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
    pokemon_api_name: str
) -> str:
    """
    Extract the form suffix from a Pokémon API name.

    Example:
    species: basculegion
    pokemon: basculegion-female
    result:  female
    """
    prefix = f"{species_api_name}-"

    if pokemon_api_name.startswith(prefix):
        return pokemon_api_name[len(prefix):]

    return ""


def format_api_suffix(suffix: str) -> str:
    """
    Turn an API suffix into a readable fallback name.
    """
    return " ".join(
        part.upper()
        if part in {"x", "y"}
        else part.capitalize()
        for part in suffix.split("-")
    )


def get_display_names(
    species_data: dict,
    pokemon_data: dict,
    distinguish_form: bool
) -> tuple[str, str]:
    """
    Build consistent names in the format:

    Species (Form)
    """

    species_name_en = (
        get_localized_name(
            species_data["names"],
            "en"
        )
        or species_data["name"]
        .replace("-", " ")
        .title()
    )

    species_name_de = (
        get_localized_name(
            species_data["names"],
            "de"
        )
        or species_name_en
    )

    if not distinguish_form:
        return species_name_en, species_name_de

    suffix = get_api_form_suffix(
        species_data["name"],
        pokemon_data["name"]
    )

    # Some default Pokémon have no form suffix.
    if not suffix:
        return species_name_en, species_name_de

    predefined_labels = FORM_LABELS.get(suffix)

    if predefined_labels:
        form_name_en, form_name_de = predefined_labels

    else:
        form_data = {}

        if pokemon_data.get("forms"):
            form_url = pokemon_data["forms"][0]["url"]

            try:
                form_data = get_json(form_url)

            except requests.RequestException as error:
                print(
                    "  Could not load form name for "
                    f"{pokemon_data['name']}: {error}"
                )

        # Only use the form suffix from PokéAPI.
        # Do not use complete form names because they can
        # be inconsistent with the species name.
        form_name_en = get_localized_name(
            form_data.get("form_names", []),
            "en"
        )

        form_name_de = get_localized_name(
            form_data.get("form_names", []),
            "de"
        )

        fallback_name = format_api_suffix(suffix)

        form_name_en = (
            form_name_en
            or fallback_name
        )

        form_name_de = (
            form_name_de
            or form_name_en
        )

    return (
        f"{species_name_en} ({form_name_en})",
        f"{species_name_de} ({form_name_de})"
    )


def get_home_sprites(
    pokemon_data: dict
) -> tuple[str | None, str | None]:
    """
    Return the normal and shiny Pokémon HOME sprites.
    """
    home_sprites = (
        pokemon_data
        .get("sprites", {})
        .get("other", {})
        .get("home", {})
    )

    normal_sprite = home_sprites.get(
        "front_default"
    )

    shiny_sprite = home_sprites.get(
        "front_shiny"
    )

    return normal_sprite, shiny_sprite


pokemon_list = []


# Load the complete species list automatically.
species_index = get_json(
    f"{API_BASE_URL}/pokemon-species"
    "?limit=10000&offset=0"
)

species_resources = species_index["results"]
species_total = len(species_resources)


for position, species_resource in enumerate(
    species_resources,
    start=1
):
    print(
        f"Loading species {position}/{species_total}: "
        f"{species_resource['name']}"
    )

    try:
        species_data = get_json(
            species_resource["url"]
        )

    except requests.RequestException as error:
        print(
            "Could not load species "
            f"{species_resource['name']}: {error}"
        )
        continue

    loaded_varieties = []

    # Load every variety belonging to the species.
    for variety in species_data["varieties"]:
        pokemon_resource = variety["pokemon"]

        try:
            pokemon_data = get_json(
                pokemon_resource["url"]
            )

        except requests.RequestException as error:
            print(
                "  Could not load variety "
                f"{pokemon_resource['name']}: {error}"
            )
            continue

        base_stats = get_base_stats(
            pokemon_data
        )

        loaded_varieties.append({
            "is_default": variety["is_default"],
            "pokemon_data": pokemon_data,
            "base_stats": base_stats,
            "signature": get_stat_signature(
                base_stats
            ),
        })

    default_variety = next(
        (
            variety
            for variety in loaded_varieties
            if variety["is_default"]
        ),
        None
    )

    if default_variety is None:
        print("  No default variety found.")
        continue

    default_signature = (
        default_variety["signature"]
    )

    # Keep the default variety and every variety
    # whose base stats differ from the default.
    relevant_varieties = [
        variety
        for variety in loaded_varieties
        if (
            variety["is_default"]
            or variety["signature"]
            != default_signature
        )
    ]

    distinguish_form = (
        len(relevant_varieties) > 1
    )

    for variety in relevant_varieties:
        pokemon_data = variety["pokemon_data"]
        base_stats = variety["base_stats"]

        name_en, name_de = get_display_names(
            species_data,
            pokemon_data,
            distinguish_form
        )

        (
            sprite_home,
            sprite_home_shiny
        ) = get_home_sprites(
            pokemon_data
        )

        sprite_home_path = download_sprite(
            sprite_home,
            NORMAL_SPRITE_DIRECTORY
            / f"{pokemon_data['name']}.png"
        )

        sprite_home_shiny_path = download_sprite(
            sprite_home_shiny,
            SHINY_SPRITE_DIRECTORY
            / f"{pokemon_data['name']}.png"
        )

        pokemon = {
            # National Pokédex number shared by forms.
            "dex": species_data["id"],

            # Unique PokéAPI ID for this variety.
            "pokemon_id": pokemon_data["id"],

            # Internal PokéAPI name.
            "api_name": pokemon_data["name"],

            "name_en": name_en,
            "name_de": name_de,

            # Pokémon HOME artwork.
            "sprite_home": sprite_home_path,
            "sprite_home_shiny": sprite_home_shiny_path,

            "base_hp": base_stats["hp"],
            "base_atk": base_stats["attack"],
            "base_def": base_stats["defense"],
            "base_spa": (
                base_stats["special-attack"]
            ),
            "base_spd": (
                base_stats["special-defense"]
            ),
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


OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

PROJECT_DIRECTORY = (
    Path(__file__).resolve().parent.parent
)

SPRITE_DIRECTORY = (
    PROJECT_DIRECTORY
    / "assets"
    / "sprites"
    / "home"
)

NORMAL_SPRITE_DIRECTORY = (
    SPRITE_DIRECTORY / "normal"
)

SHINY_SPRITE_DIRECTORY = (
    SPRITE_DIRECTORY / "shiny"
)

with OUTPUT_FILE.open(
    "w",
    encoding="utf-8"
) as file:
    json.dump(
        pokemon_list,
        file,
        ensure_ascii=False,
        indent=4
    )


print()
print(
    f"Done! Imported "
    f"{len(pokemon_list)} entries."
)
print(f"Saved to: {OUTPUT_FILE}")