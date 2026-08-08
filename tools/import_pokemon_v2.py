"""Build the nested Pokédex data file from PokéAPI.

Version 4: curated form names and explicit cosmetic-form retention.

This importer deliberately writes ``data/pokemon_v2.json`` so the existing
Defensive Spread Optimizer can keep using the legacy ``data/pokemon.json``.
Evolution links are stored on species entries so the Pokédex can include moves
inherited from pre-evolutions without a separate evolution data file.
"""

from __future__ import annotations

import argparse
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


API_BASE_URL = "https://pokeapi.co/api/v2"
PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
DATA_DIRECTORY = PROJECT_DIRECTORY / "data"
OUTPUT_FILE = DATA_DIRECTORY / "pokemon_v2.json"
PREVIEW_OUTPUT_FILE = DATA_DIRECTORY / "pokemon_v2_preview.json"

SPRITE_DIRECTORY = PROJECT_DIRECTORY / "assets" / "sprites" / "home"
NORMAL_SPRITE_DIRECTORY = SPRITE_DIRECTORY / "normal"
SHINY_SPRITE_DIRECTORY = SPRITE_DIRECTORY / "shiny"

REQUEST_TIMEOUT_SECONDS = 30

STAT_NAMES = {
    "hp": "hp",
    "attack": "atk",
    "defense": "def",
    "special-attack": "spa",
    "special-defense": "spd",
    "speed": "spe",
}

STAT_KEY_ORDER = ("hp", "atk", "def", "spa", "spd", "spe")


# Full display-name overrides for forms whose upstream labels are incomplete,
# misleading, or redundant. Values are: (English name, German name).
FORM_DISPLAY_NAME_OVERRIDES = {
    "calyrex-ice": (
        "Calyrex (Ice Rider)",
        "Coronospa (Schimmelreiter)",
    ),
    "calyrex-shadow": (
        "Calyrex (Shadow Rider)",
        "Coronospa (Rappenreiter)",
    ),
    "tauros-paldea-combat-breed": (
        "Tauros (Paldean Form (Combat Breed))",
        "Paldea-Tauros",
    ),
    "tauros-paldea-blaze-breed": (
        "Tauros (Paldean Form (Blaze Breed))",
        "Paldea-Tauros (Flammenvariante)",
    ),
    "tauros-paldea-aqua-breed": (
        "Tauros (Paldean Form (Aqua Breed))",
        "Paldea-Tauros (Flutenvariante)",
    ),
    "absol-mega-z": (
        "Absol (Mega Z)",
        "Absol (Mega Z)",
    ),
    "garchomp-mega-z": (
        "Garchomp (Mega Z)",
        "Knakrack (Mega Z)",
    ),
    "lucario-mega-z": (
        "Lucario (Mega Z)",
        "Lucario (Mega Z)",
    ),

    # Meowstic / Psiaugon.
    "meowstic-male": (
        "Meowstic (Male)",
        "Psiaugon (Männlich)",
    ),
    "meowstic-female": (
        "Meowstic (Female)",
        "Psiaugon (Weiblich)",
    ),

    # Hoopa.
    "hoopa-unbound": (
        "Hoopa (Unbound)",
        "Hoopa (Entfesselt)",
    ),

    # Eiscue / Kubuin.
    "eiscue-ice": (
        "Eiscue (Ice Face)",
        "Kubuin (Tiefkühlkopf)",
    ),
    "eiscue-noice": (
        "Eiscue (Noice Face)",
        "Kubuin (Wohlfühlkopf)",
    ),
}


# Let's Go partner forms are intentionally omitted from the shared Pokédex.
EXCLUDED_VARIETY_API_NAMES = {
    "pikachu-partner",
    "eevee-partner",
}


# Keep these visually distinct form families as separate Pokédex entries even
# when two forms are mechanically identical.
FORCE_KEEP_VARIETY_PREFIXES = (
    "squawkabilly-",
    "tatsugiri-",
)


# Consistent labels for common form suffixes used by PokéAPI.
# Order: English, German.
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
    "single-strike": ("Single Strike", "Fokussierter Stil"),
    "rapid-strike": ("Rapid Strike", "Fließender Stil"),
    "chest": ("Chest", "Truhe"),
    "roaming": ("Roaming", "Wander"),
    "bloodmoon": ("Bloodmoon", "Blutmond"),
    "terastal": ("Terastal", "Terakristall"),
    "stellar": ("Stellar", "Stellar"),
}


def create_session() -> requests.Session:
    """Create a session that retries temporary PokéAPI errors."""
    retry = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    adapter = HTTPAdapter(max_retries=retry)

    api_session = requests.Session()
    api_session.headers.update(
        {"User-Agent": "Cordys-Lab-Pokedex/0.1"}
    )
    api_session.mount("https://", adapter)
    return api_session


session = create_session()


@lru_cache(maxsize=None)
def get_json(url: str) -> dict[str, Any]:
    """Load and cache one JSON resource from PokéAPI."""
    response = session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()


def get_resource_id(resource: dict[str, Any] | None) -> int | None:
    """Extract the numeric PokéAPI ID from a named API resource."""
    if not isinstance(resource, dict):
        return None

    url = resource.get("url")
    if not isinstance(url, str) or not url:
        return None

    try:
        return int(url.rstrip("/").rsplit("/", 1)[-1])
    except ValueError as error:
        raise ValueError(f"Invalid PokéAPI resource URL: {url}") from error


def get_localized_name(
    entries: list[dict[str, Any]],
    language: str,
) -> str:
    """Return a localized name from a PokéAPI names list."""
    for entry in entries:
        if entry.get("language", {}).get("name") == language:
            return entry.get("name", "")
    return ""


def format_api_name(api_name: str) -> str:
    """Turn a PokéAPI identifier into a readable fallback label."""
    return " ".join(
        part.upper() if part in {"x", "y"} else part.capitalize()
        for part in api_name.split("-")
    )


def get_species_names(
    species_data: dict[str, Any],
) -> tuple[str, str]:
    """Return the English and German species names."""
    name_en = (
        get_localized_name(species_data.get("names", []), "en")
        or format_api_name(species_data["name"])
    )
    name_de = (
        get_localized_name(species_data.get("names", []), "de")
        or name_en
    )
    return name_en, name_de


def get_api_form_suffix(
    species_api_name: str,
    pokemon_api_name: str,
) -> str:
    """Extract the form suffix from a Pokémon API name."""
    prefix = f"{species_api_name}-"
    if pokemon_api_name.startswith(prefix):
        return pokemon_api_name[len(prefix):]
    return ""


def load_form_data(
    pokemon_data: dict[str, Any],
) -> dict[str, Any]:
    """Load the first PokemonForm resource for localized form names."""
    forms = pokemon_data.get("forms", [])
    if not forms:
        return {}

    form_url = forms[0].get("url")
    if not form_url:
        return {}

    try:
        return get_json(form_url)
    except requests.RequestException as error:
        # Form labels are optional. The API suffix remains a safe fallback.
        print(
            "  Warning: could not load localized form name for "
            f"{pokemon_data['name']}: {error}"
        )
        return {}


def get_form_labels(
    species_data: dict[str, Any],
    pokemon_data: dict[str, Any],
) -> tuple[str, str]:
    """Return short English and German labels for one form."""
    suffix = get_api_form_suffix(
        species_data["name"],
        pokemon_data["name"],
    )
    if not suffix:
        return "", ""

    predefined_labels = FORM_LABELS.get(suffix)
    if predefined_labels:
        return predefined_labels

    form_data = load_form_data(pokemon_data)
    form_names = form_data.get("form_names", [])

    fallback = format_api_name(suffix)
    name_en = get_localized_name(form_names, "en") or fallback
    name_de = get_localized_name(form_names, "de") or name_en
    return name_en, name_de


def get_dynamic_form_display_name_override(
    api_name: str,
) -> tuple[str, str] | None:
    """Return curated names for form families with variable API suffixes."""
    tokens = set(api_name.split("-"))

    # Mega Meowstic has one shared Mega form.
    if api_name.startswith("meowstic-") and "mega" in tokens:
        return (
            "Meowstic (Mega)",
            "Psiaugon (Mega)",
        )

    # Squawkabilly / Krawalloro: retain and name all four plumages.
    if api_name.startswith("squawkabilly-"):
        plumage_names = {
            "green": ("Green Plumage", "Grüngefiedert"),
            "blue": ("Blue Plumage", "Blaugefiedert"),
            "yellow": ("Yellow Plumage", "Gelbgefiedert"),
            "white": ("White Plumage", "Weißgefiedert"),
        }
        for token, (name_en, name_de) in plumage_names.items():
            if token in tokens:
                return (
                    f"Squawkabilly ({name_en})",
                    f"Krawalloro ({name_de})",
                )

    # Tatsugiri / Nigiragi: retain all three base forms and all three Mega
    # forms. Token order is ignored so this also tolerates upstream renames.
    if api_name.startswith("tatsugiri-"):
        form_names = {
            "curly": ("Curly Form", "Gebogene Form"),
            "droopy": ("Droopy Form", "Hängende Form"),
            "stretchy": ("Stretchy Form", "Gestreckte Form"),
        }
        for token, (name_en, name_de) in form_names.items():
            if token not in tokens:
                continue

            if "mega" in tokens:
                return (
                    f"Tatsugiri (Mega {name_en})",
                    f"Nigiragi (Mega {name_de})",
                )

            return (
                f"Tatsugiri ({name_en})",
                f"Nigiragi ({name_de})",
            )

    return None


def get_form_display_names(
    species_data: dict[str, Any],
    pokemon_data: dict[str, Any],
    distinguish_form: bool,
) -> tuple[str, str]:
    """Build full English and German display names for one variety."""
    api_name = str(pokemon_data.get("name", ""))
    override = FORM_DISPLAY_NAME_OVERRIDES.get(api_name)
    if override is not None:
        return override

    dynamic_override = get_dynamic_form_display_name_override(api_name)
    if dynamic_override is not None:
        return dynamic_override

    species_name_en, species_name_de = get_species_names(species_data)
    if not distinguish_form:
        return species_name_en, species_name_de

    form_name_en, form_name_de = get_form_labels(
        species_data,
        pokemon_data,
    )
    if not form_name_en:
        return species_name_en, species_name_de

    return (
        f"{species_name_en} ({form_name_en})",
        f"{species_name_de} ({form_name_de})",
    )


def get_base_stats(pokemon_data: dict[str, Any]) -> dict[str, int]:
    """Convert PokéAPI stat names to the six project stat keys."""
    base_stats = {
        STAT_NAMES[stat["stat"]["name"]]: stat["base_stat"]
        for stat in pokemon_data.get("stats", [])
        if stat.get("stat", {}).get("name") in STAT_NAMES
    }

    if set(base_stats) != set(STAT_NAMES.values()):
        raise ValueError(
            f"Incomplete base stats for {pokemon_data['name']}: "
            f"{sorted(base_stats)}"
        )
    return base_stats


def get_types(pokemon_data: dict[str, Any]) -> list[str]:
    """Return the form's type identifiers in slot order."""
    return [
        entry["type"]["name"]
        for entry in sorted(
            pokemon_data.get("types", []),
            key=lambda item: item["slot"],
        )
    ]


def get_abilities(
    pokemon_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return abilities with DE/EN names and hidden-ability flags."""
    abilities = []

    for entry in sorted(
        pokemon_data.get("abilities", []),
        key=lambda item: item["slot"],
    ):
        ability_resource = entry["ability"]
        ability_data = get_json(ability_resource["url"])
        api_name = ability_resource["name"]

        name_en = (
            get_localized_name(ability_data.get("names", []), "en")
            or format_api_name(api_name)
        )
        name_de = (
            get_localized_name(ability_data.get("names", []), "de")
            or name_en
        )

        abilities.append(
            {
                "api_name": api_name,
                "name_en": name_en,
                "name_de": name_de,
                "is_hidden": entry["is_hidden"],
                "slot": entry["slot"],
            }
        )

    return abilities


def get_mechanical_signature(
    pokemon_data: dict[str, Any],
) -> tuple[Any, ...]:
    """Return the fields that make a variety relevant to our battle tools.

    PokéAPI also exposes costume, Totem and other special varieties that are
    mechanically identical to another variety of the same species. They do
    not need separate records in the Champions Pokédex. Regional and other
    meaningful forms remain distinct when their types, stats or abilities
    differ.
    """
    base_stats = get_base_stats(pokemon_data)
    stats_signature = tuple(
        base_stats[stat_name]
        for stat_name in STAT_KEY_ORDER
    )
    types_signature = tuple(get_types(pokemon_data))
    abilities_signature = tuple(
        (
            entry["ability"]["name"],
            entry["is_hidden"],
            entry["slot"],
        )
        for entry in sorted(
            pokemon_data.get("abilities", []),
            key=lambda item: item["slot"],
        )
    )

    return (
        stats_signature,
        types_signature,
        abilities_signature,
    )


def select_distinct_varieties(
    species_data: dict[str, Any],
) -> tuple[
    list[tuple[dict[str, Any], dict[str, Any]]],
    list[tuple[str, str]],
]:
    """Keep one representative of each mechanical variety.

    The default variety is considered first. Remaining varieties are ordered
    by PokéAPI ID, so an ordinary form such as ``raticate-alola`` is retained
    before its later duplicate ``raticate-totem-alola``.
    """
    loaded_varieties = [
        (variety, get_json(variety["pokemon"]["url"]))
        for variety in species_data.get("varieties", [])
    ]
    loaded_varieties.sort(
        key=lambda item: (
            not item[0]["is_default"],
            item[1]["id"],
        )
    )

    retained_varieties = []
    for variety, pokemon_data in loaded_varieties:
        api_name = str(pokemon_data.get("name", ""))
        if api_name in EXCLUDED_VARIETY_API_NAMES:
            print(
                f"  Excluding {api_name}: partner form not used "
                "in the Cordy's Lab Pokédex"
            )
            continue
        retained_varieties.append((variety, pokemon_data))

    loaded_varieties = retained_varieties

    selected = []
    skipped = []
    representatives: dict[tuple[Any, ...], str] = {}

    for variety, pokemon_data in loaded_varieties:
        api_name = str(pokemon_data.get("name", ""))

        if api_name.startswith(FORCE_KEEP_VARIETY_PREFIXES):
            selected.append((variety, pokemon_data))
            continue

        signature = get_mechanical_signature(pokemon_data)
        representative_name = representatives.get(signature)

        if representative_name is not None:
            skipped.append(
                (pokemon_data["name"], representative_name)
            )
            continue

        representatives[signature] = pokemon_data["name"]
        selected.append((variety, pokemon_data))

    return selected, skipped


def get_home_sprite_urls(
    pokemon_data: dict[str, Any],
) -> tuple[str | None, str | None]:
    """Return normal and shiny HOME sprite URLs."""
    home_sprites = (
        pokemon_data.get("sprites", {})
        .get("other", {})
        .get("home", {})
    )
    return (
        home_sprites.get("front_default"),
        home_sprites.get("front_shiny"),
    )


def download_sprite(
    url: str | None,
    destination: Path,
) -> str | None:
    """Download an original HOME sprite and return its project path."""
    if not url:
        return None

    destination.parent.mkdir(parents=True, exist_ok=True)

    if not destination.exists():
        response = session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        destination.write_bytes(response.content)

    return destination.relative_to(PROJECT_DIRECTORY).as_posix()


def build_form(
    species_data: dict[str, Any],
    variety: dict[str, Any],
    pokemon_data: dict[str, Any],
    distinguish_form: bool,
) -> dict[str, Any]:
    """Build one nested form entry."""
    name_en, name_de = get_form_display_names(
        species_data,
        pokemon_data,
        distinguish_form,
    )

    normal_url, shiny_url = get_home_sprite_urls(pokemon_data)
    filename = f"{pokemon_data['name']}.png"

    return {
        "pokemon_id": pokemon_data["id"],
        "api_name": pokemon_data["name"],
        "name_en": name_en,
        "name_de": name_de,
        "is_default": variety["is_default"],
        "types": get_types(pokemon_data),
        "base_stats": get_base_stats(pokemon_data),
        "abilities": get_abilities(pokemon_data),
        "sprites": {
            "home": download_sprite(
                normal_url,
                NORMAL_SPRITE_DIRECTORY / filename,
            ),
            "home_shiny": download_sprite(
                shiny_url,
                SHINY_SPRITE_DIRECTORY / filename,
            ),
        },
    }


def build_species(
    species_data: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    """Build one National Pokédex entry with all its varieties."""
    varieties = species_data.get("varieties", [])
    if not varieties:
        raise ValueError(
            f"Species {species_data['name']} has no varieties."
        )

    selected_varieties, skipped_varieties = select_distinct_varieties(
        species_data
    )

    for skipped_name, representative_name in skipped_varieties:
        print(
            f"  Skipping {skipped_name}: mechanically identical to "
            f"{representative_name}"
        )

    name_en, name_de = get_species_names(species_data)
    distinguish_form = len(selected_varieties) > 1

    forms = [
        build_form(
            species_data,
            variety,
            pokemon_data,
            distinguish_form,
        )
        for variety, pokemon_data in selected_varieties
    ]
    forms.sort(
        key=lambda form: (
            not form["is_default"],
            form["pokemon_id"],
        )
    )

    return (
        {
            "dex": species_data["id"],
            "api_name": species_data["name"],
            "name_en": name_en,
            "name_de": name_de,
            "evolves_from_species_id": get_resource_id(
                species_data.get("evolves_from_species")
            ),
            "forms": forms,
        },
        len(skipped_varieties),
    )


def validate_pokemon_data(pokemon_list: list[dict[str, Any]]) -> None:
    """Reject duplicate or incomplete entries before writing the file."""
    dex_numbers: set[int] = set()
    pokemon_ids: set[int] = set()
    api_names: set[str] = set()

    for species in pokemon_list:
        dex_number = species["dex"]
        if dex_number in dex_numbers:
            raise ValueError(f"Duplicate National Dex number: {dex_number}")
        dex_numbers.add(dex_number)

        parent_species_id = species.get("evolves_from_species_id")
        if parent_species_id is not None and not isinstance(parent_species_id, int):
            raise ValueError(
                f"Invalid evolves_from_species_id for Dex #{dex_number}: "
                f"{parent_species_id!r}"
            )

        forms = species.get("forms", [])
        if not forms:
            raise ValueError(f"No forms stored for Dex #{dex_number}")

        default_count = sum(form["is_default"] for form in forms)
        if default_count != 1:
            raise ValueError(
                f"Dex #{dex_number} has {default_count} default forms."
            )

        for form in forms:
            pokemon_id = form["pokemon_id"]
            api_name = form["api_name"]

            if pokemon_id in pokemon_ids:
                raise ValueError(f"Duplicate Pokémon ID: {pokemon_id}")
            if api_name in api_names:
                raise ValueError(f"Duplicate API name: {api_name}")

            pokemon_ids.add(pokemon_id)
            api_names.add(api_name)


def write_json_atomically(
    data: list[dict[str, Any]],
    output_file: Path,
) -> None:
    """Write complete JSON first, then replace the target in one step."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = output_file.with_name(
        f"{output_file.stem}.tmp{output_file.suffix}"
    )

    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
        file.write("\n")

    temporary_file.replace(output_file)


def import_pokemon(
    limit: int | None = None,
) -> tuple[Path, int, int, int]:
    """Load the Pokédex and return output path, species count, form count."""
    species_index = get_json(
        f"{API_BASE_URL}/pokemon-species?limit=10000&offset=0"
    )
    species_resources = species_index["results"]

    if limit is not None:
        if limit < 1:
            raise ValueError("--limit must be at least 1.")
        species_resources = species_resources[:limit]

    pokemon_list = []
    skipped_form_count = 0
    species_total = len(species_resources)

    for position, species_resource in enumerate(species_resources, start=1):
        print(
            f"Loading species {position}/{species_total}: "
            f"{species_resource['name']}"
        )
        species_data = get_json(species_resource["url"])
        species_entry, skipped_count = build_species(species_data)
        pokemon_list.append(species_entry)
        skipped_form_count += skipped_count

    pokemon_list.sort(key=lambda species: species["dex"])
    validate_pokemon_data(pokemon_list)

    output_file = PREVIEW_OUTPUT_FILE if limit is not None else OUTPUT_FILE
    write_json_atomically(pokemon_list, output_file)

    form_count = sum(len(species["forms"]) for species in pokemon_list)
    return (
        output_file,
        len(pokemon_list),
        form_count,
        skipped_form_count,
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Import nested Pokémon, evolution, form, type, stat, ability "
            "and sprite data from PokéAPI."
        )
    )
    parser.add_argument(
        "--limit",
        type=int,
        help=(
            "Import only the first N species and write "
            "pokemon_v2_preview.json."
        ),
    )
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    (
        output_file,
        species_count,
        form_count,
        skipped_form_count,
    ) = import_pokemon(limit=arguments.limit)

    print()
    print(
        f"Done! Imported {species_count} species "
        f"with {form_count} forms."
    )
    print(
        f"Skipped {skipped_form_count} mechanically identical forms."
    )
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    main()