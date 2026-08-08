"""Import localized ability names and descriptions from PokéAPI.

The standalone ``data/abilities.json`` keeps descriptions out of the nested
Pokémon file, where the same ability would otherwise be repeated for every
Pokémon and form.

Run from the project root with:

    python3 tools/import_abilities.py
"""

from __future__ import annotations

import argparse
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


IMPORTER_VERSION = "v4"
API_BASE_URL = "https://pokeapi.co/api/v2"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "abilities.json"
REQUEST_TIMEOUT_SECONDS = 30

# Localized in-game text is retained as a fallback. For the Pokédex itself,
# the more detailed effect entries are preferred because VGC players need
# exact chances, multipliers, stat stages, triggers, and thresholds.
VERSION_GROUP_PRIORITY = (
    "scarlet-violet",
    "legends-arceus",
    "brilliant-diamond-and-shining-pearl",
    "sword-shield",
    "lets-go-pikachu-lets-go-eevee",
    "ultra-sun-ultra-moon",
    "sun-moon",
    "omega-ruby-alpha-sapphire",
    "x-y",
    "black-2-white-2",
    "black-white",
)

# PokéAPI currently has no official German in-game text for several newer
# abilities. These carefully translated fallbacks are used until one becomes
# available from the API.
GERMAN_DESCRIPTION_FALLBACKS = {
    "lingering-aroma": (
        "Bei Kontakt wird die Fähigkeit des Angreifers zu Duftschwade."
    ),
    "seed-sower": (
        "Wird das Pokémon von einer Attacke getroffen, erzeugt es ein Grasfeld."
    ),
    "thermal-exchange": (
        "Erhöht den Angriff, wenn das Pokémon von einer Feuer-Attacke getroffen "
        "wird. Außerdem kann es nicht verbrannt werden."
    ),
    "anger-shell": (
        "Fallen die KP unter die Hälfte, sinken Verteidigung und "
        "Spezial-Verteidigung, während Angriff, Spezial-Angriff und Initiative "
        "steigen."
    ),
    "purifying-salt": (
        "Schützt vor Statusproblemen und halbiert den Schaden durch "
        "Geist-Attacken."
    ),
    "well-baked-body": (
        "Verleiht Immunität gegen Feuer-Attacken und erhöht die Verteidigung "
        "stark, wenn das Pokémon von einer solchen Attacke getroffen wird."
    ),
    "wind-rider": (
        "Verleiht Immunität gegen Wind-Attacken und erhöht den Angriff um eine "
        "Stufe, wenn das Pokémon von einer solchen Attacke getroffen wird."
    ),
    "guard-dog": (
        "Erhöht den Angriff, wenn das Pokémon eingeschüchtert wird, und "
        "verhindert, dass es zum Auswechseln gezwungen wird."
    ),
    "rocky-payload": "Verstärkt Gestein-Attacken.",
    "wind-power": (
        "Wird das Pokémon von einer Wind-Attacke getroffen, verdoppelt sich die "
        "Stärke seiner nächsten Elektro-Attacke."
    ),
    "zero-to-hero": "Beim Auswechseln wechselt das Pokémon in seine Heldenform.",
    "commander": (
        "Befindet sich ein verbündetes Heerashai auf dem Feld, springt das "
        "Pokémon in dessen Maul."
    ),
    "electromorphosis": (
        "Wird das Pokémon von einer Attacke getroffen, verdoppelt sich die "
        "Stärke seiner nächsten Elektro-Attacke."
    ),
    "protosynthesis": (
        "Erhöht bei starkem Sonnenlicht oder durch eine getragene Energiekapsel "
        "den höchsten Statuswert."
    ),
    "quark-drive": (
        "Erhöht im Elektrofeld oder durch eine getragene Energiekapsel den "
        "höchsten Statuswert."
    ),
    "good-as-gold": "Verleiht Immunität gegen Status-Attacken.",
    "vessel-of-ruin": (
        "Senkt den Spezial-Angriff aller Pokémon außer dem eigenen."
    ),
    "sword-of-ruin": "Senkt die Verteidigung aller Pokémon außer dem eigenen.",
    "tablets-of-ruin": "Senkt den Angriff aller Pokémon außer dem eigenen.",
    "beads-of-ruin": (
        "Senkt die Spezial-Verteidigung aller Pokémon außer dem eigenen."
    ),
    "orichalcum-pulse": (
        "Erzeugt beim Kampfantritt starkes Sonnenlicht und erhöht den Angriff, "
        "solange es anhält."
    ),
    "hadron-engine": (
        "Erzeugt beim Kampfantritt ein Elektrofeld und erhöht den "
        "Spezial-Angriff, solange es besteht."
    ),
    "opportunist": "Kopiert Statuswerterhöhungen des Gegners.",
    "cud-chew": (
        "Bewirkt, dass das Pokémon eine bereits verzehrte Beere am Ende der "
        "nächsten Runde erneut einsetzt."
    ),
    "sharpness": "Verstärkt Schnitt-Attacken.",
    "supreme-overlord": (
        "Erhöht Angriff und Spezial-Angriff für jedes bereits besiegte Pokémon "
        "im eigenen Team."
    ),
    "costar": (
        "Kopiert beim Kampfantritt die Statuswertveränderungen des Mitstreiters."
    ),
    "toxic-debris": (
        "Verstreut Giftspitzen auf der gegnerischen Seite, wenn das Pokémon "
        "durch eine physische Attacke Schaden erleidet."
    ),
    "armor-tail": (
        "Hindert Gegner daran, Attacken mit erhöhter Priorität wie Ruckzuckhieb "
        "einzusetzen."
    ),
    "earth-eater": (
        "Stellt KP wieder her, wenn das Pokémon von einer Boden-Attacke "
        "getroffen wird."
    ),
    "mycelium-might": (
        "Status-Attacken werden zuletzt ausgeführt, bleiben dafür aber von der "
        "Fähigkeit des Gegners unbeeinflusst."
    ),
    "minds-eye": (
        "Ignoriert Änderungen am gegnerischen Ausweichwert, verhindert das "
        "Senken der eigenen Genauigkeit und lässt Normal- sowie Kampf-Attacken "
        "Geist-Pokémon treffen."
    ),
    "supersweet-syrup": (
        "Senkt beim ersten Kampfantritt den Ausweichwert aller angrenzenden "
        "Gegner um eine Stufe."
    ),
    "hospitality": (
        "Stellt beim Kampfantritt 25 % der maximalen KP eines Mitstreiters "
        "wieder her."
    ),
    "toxic-chain": (
        "Attacken des Pokémon können den getroffenen Gegner schwer vergiften."
    ),
    "embody-aspect": (
        "Erhöht abhängig von der Form eines terakristallisierten Ogerpon einen "
        "bestimmten Statuswert."
    ),
    "tera-shift": (
        "Beim Kampfantritt wechselt Terapagos bis zum Kampfende in seine "
        "Terakristall-Form."
    ),
    "tera-shell": (
        "Schadensattacken, die das Pokémon bei vollen KP treffen, sind nicht "
        "sehr effektiv."
    ),
    "teraform-zero": (
        "Sobald Terapagos seine Stellarform annimmt, neutralisiert es sofort "
        "Wetter- und Feldeffekte."
    ),
    "poison-puppeteer": (
        "Pokémon, die durch Attacken von Infamomo vergiftet werden, werden "
        "zusätzlich verwirrt."
    ),
}

# PokéAPI still exposes several German names that were replaced in Generation
# IX. Keep the current names stable even when the source data is refreshed.
CURRENT_GERMAN_NAME_OVERRIDES: dict[str, str] = {
    "symbiosis": "Symbiose",
    "own-tempo": "Gleichmut",
    "snow-warning": "Schneeschauer",
    "poison-heal": "Giftheilung",
    "tangled-feet": "Taumelschritt",
}

# The detailed PokéAPI translations are useful, but a small number are
# grammatically broken, mechanically outdated, or too ambiguous for a VGC
# reference. These concise overrides retain the detailed style while making
# the relevant number and trigger explicit.
PRECISE_GERMAN_DESCRIPTION_OVERRIDES: dict[str, str] = {
    "stench": (
        "Bei jedem Treffer besteht eine Chance von 10 %, das Ziel "
        "zurückschrecken zu lassen."
    ),
    "static": (
        "Wird das Pokémon von einer Kontaktattacke getroffen, besteht eine "
        "Chance von 30 %, den Angreifer zu paralysieren."
    ),
    "compound-eyes": (
        "Erhöht die Genauigkeit eigener Attacken um den Faktor 1,3."
    ),
    "effect-spore": (
        "Wird das Pokémon von einer Kontaktattacke getroffen, besteht eine "
        "Chance von 30 %, den Angreifer einzuschläfern, zu paralysieren oder "
        "zu vergiften."
    ),
    "intimidate": (
        "Senkt beim Einwechseln den Angriff aller angrenzenden gegnerischen "
        "Pokémon um 1 Stufe."
    ),
    "drizzle": "Erzeugt beim Einwechseln für 5 Runden Regen.",
    "sand-stream": "Erzeugt beim Einwechseln für 5 Runden Sandsturm.",
    "drought": "Erzeugt beim Einwechseln für 5 Runden Sonnenschein.",
    "snow-warning": "Erzeugt beim Einwechseln für 5 Runden Schnee.",
    "sand-veil": (
        "Senkt im Sandsturm die Genauigkeit gegnerischer Attacken gegen das "
        "Pokémon auf das 0,8-Fache."
    ),
    "snow-cloak": (
        "Senkt bei Schnee die Genauigkeit gegnerischer Attacken gegen das "
        "Pokémon auf das 0,8-Fache."
    ),
    "rain-dish": (
        "Regeneriert bei Regen am Ende jeder Runde 1/16 der maximalen KP."
    ),
    "ice-body": (
        "Regeneriert bei Schnee am Ende jeder Runde 1/16 der maximalen KP."
    ),
    "sand-rush": "Verdoppelt im Sandsturm die Initiative.",
    "slush-rush": "Verdoppelt bei Schnee die Initiative.",
    "natural-cure": "Heilt beim Auswechseln das Statusproblem des Pokémon.",
    "own-tempo": (
        "Verhindert Verwirrung und schützt vor der Angriffssenkung durch "
        "Bedroher."
    ),
    "poison-point": (
        "Wird das Pokémon von einer Kontaktattacke getroffen, besteht eine "
        "Chance von 30 %, den Angreifer zu vergiften."
    ),
    "guts": (
        "Erhöht den Angriff um den Faktor 1,5, wenn das Pokémon von einem "
        "Statusproblem betroffen ist. Ignoriert dabei die Angriffssenkung "
        "durch Verbrennung."
    ),
    "marvel-scale": (
        "Erhöht die Verteidigung um den Faktor 1,5, wenn das Pokémon von "
        "einem Statusproblem betroffen ist."
    ),
    "hustle": (
        "Erhöht den Angriff um den Faktor 1,5, senkt aber die Genauigkeit "
        "physischer Attacken auf das 0,8-Fache."
    ),
    "rivalry": (
        "Verstärkt Attacken gegen Pokémon gleichen Geschlechts um den Faktor "
        "1,25 und schwächt sie gegen Pokémon anderen Geschlechts auf den "
        "Faktor 0,75."
    ),
    "poison-heal": (
        "Regeneriert am Ende jeder Runde 1/8 der maximalen KP, wenn das "
        "Pokémon vergiftet ist; Giftschaden wird dabei verhindert."
    ),
    "hydration": (
        "Heilt bei Regen am Ende jeder Runde das Statusproblem des Pokémon."
    ),
    "quick-feet": (
        "Erhöht die Initiative um den Faktor 1,5, wenn das Pokémon von einem "
        "Statusproblem betroffen ist; die Initiative wird bei Paralyse nicht "
        "gesenkt."
    ),
    "technician": (
        "Verstärkt Attacken mit einer Basisstärke von höchstens 60 um den "
        "Faktor 1,5."
    ),
    "leaf-guard": (
        "Schützt das Pokémon bei Sonnenschein vor Statusproblemen."
    ),
    "healer": (
        "Heilt am Ende jeder Runde mit einer Chance von 30 % das "
        "Statusproblem eines angrenzenden Mitstreiters."
    ),
    "friend-guard": (
        "Verringert den Schaden, den Mitstreiter durch Attacken erleiden, um "
        "25 %."
    ),
    "refrigerate": (
        "Normal-Attacken werden zu Eis-Attacken und um den Faktor 1,2 "
        "verstärkt."
    ),
    "pixilate": (
        "Normal-Attacken werden zu Feen-Attacken und um den Faktor 1,2 "
        "verstärkt."
    ),
    "aerilate": (
        "Normal-Attacken werden zu Flug-Attacken und um den Faktor 1,2 "
        "verstärkt."
    ),
    "parental-bond": (
        "Lässt geeignete Einzelziel-Attacken zweimal treffen; der zweite "
        "Treffer verursacht 25 % des normalen Schadens."
    ),
    "tough-claws": (
        "Verstärkt Kontaktattacken um den Faktor 1,3."
    ),
    "galvanize": (
        "Normal-Attacken werden zu Elektro-Attacken und um den Faktor 1,2 "
        "verstärkt."
    ),
    "steelworker": "Verstärkt Stahl-Attacken um den Faktor 1,5.",
    "battery": (
        "Verstärkt die Spezial-Attacken von Mitstreitern um den Faktor 1,3."
    ),
    "stakeout": (
        "Verdoppelt den Schaden gegen ein Ziel in der Runde, in der es "
        "eingewechselt wurde."
    ),
    "neuroforce": (
        "Verstärkt sehr effektive Attacken um den Faktor 1,25."
    ),
    "power-spot": (
        "Verstärkt die Attacken von Mitstreitern um den Faktor 1,3."
    ),
    "steely-spirit": (
        "Verstärkt Stahl-Attacken auf der eigenen Seite um den Faktor 1,5."
    ),
    "transistor": "Verstärkt Elektro-Attacken um den Faktor 1,3.",
    "rocky-payload": "Verstärkt Gesteins-Attacken um den Faktor 1,5.",
    "sharpness": "Verstärkt Schnitt-Attacken um den Faktor 1,5.",
    "supreme-overlord": (
        "Verstärkt Attacken für jedes bereits besiegte Pokémon im eigenen "
        "Team um 10 %, höchstens jedoch um 50 %."
    ),
}


GERMAN_TEXT_REPLACEMENTS = (
    ("Schütz vor ", "Schützt vor "),
    ("Versärkt ", "Verstärkt "),
    ("erhöhrt", "erhöht"),
    ("Statuswerte-Änderungen", "Statuswertänderungen"),
    ("K.O.Attacke", "K.-o.-Attacke"),
    ("K.O.-Attacke", "K.-o.-Attacke"),
    ("K.O.-Treffer", "K.-o.-Treffer"),
    ("der max KP", "der maximalen KP"),
    ("die max KP", "die maximalen KP"),
    ("seiner max KP", "seiner maximalen KP"),
    ("ihrer max KP", "ihrer maximalen KP"),
    ("Fluchtwert", "Ausweichwert"),
    ("ein zweites mal", "ein zweites Mal"),
    ("die Stärkste Attacke", "die stärkste Attacke"),
    (
        "Beschützt verbündete Pflanze Pokémon for negativen "
        "Statuswerteänderungenen.",
        "Schützt verbündete Pflanzen-Pokémon vor negativen "
        "Statuswertveränderungen.",
    ),
)

GERMAN_ATTACK_TYPE_NAMES = (
    "Normal",
    "Feuer",
    "Wasser",
    "Elektro",
    "Pflanze",
    "Eis",
    "Kampf",
    "Gift",
    "Boden",
    "Flug",
    "Psycho",
    "Käfer",
    "Gestein",
    "Geist",
    "Drache",
    "Unlicht",
    "Stahl",
    "Fee",
)

# PokéAPI is the source for established abilities. These six abilities were
# introduced in Pokémon Champions and are curated separately because the API
# still contains incomplete localization for some of them. Applying the
# overrides after every import also prevents future refreshes from reverting
# official German names or the complete Piercing Drill effect.
CHAMPIONS_ABILITY_OVERRIDES: dict[str, dict[str, str]] = {
    "piercing-drill": {
        "name_en": "Piercing Drill",
        "name_de": "Stichbohrer",
        "description_en": (
            "When the Pokémon uses contact moves, it can hit even targets "
            "that are protecting themselves, dealing 1/4 of the damage that "
            "the move would otherwise deal. Everything aside from the "
            "target's protective effects is still triggered."
        ),
        "description_de": (
            "Setzt das Pokémon eine Kontaktattacke ein, trifft sie auch Ziele, "
            "die sich selbst schützen, und fügt ihnen 1/4 des eigentlichen "
            "Schadens zu. Alle anderen Effekte werden trotzdem ausgelöst."
        ),
    },
    "dragonize": {
        "name_en": "Dragonize",
        "name_de": "Drachenschicht",
        "description_en": (
            "The Pokémon's Normal-type moves become Dragon-type moves and "
            "their power is boosted by 20%."
        ),
        "description_de": (
            "Normal-Attacken des Pokémon nehmen den Typ Drache an und ihre "
            "Stärke wird um 20 % erhöht."
        ),
    },
    "mega-sol": {
        "name_en": "Mega Sol",
        "name_de": "Mega-Solarladung",
        "description_en": (
            "The Pokémon can use its moves as if the weather were harsh "
            "sunlight."
        ),
        "description_de": (
            "Das Pokémon kann Attacken wie bei Sonnenschein einsetzen, auch "
            "wenn nicht das Wetter Sonnenschein herrscht."
        ),
    },
    "spicy-spray": {
        "name_en": "Spicy Spray",
        "name_de": "Chilispritzer",
        "description_en": (
            "When the Pokémon takes damage from a move, it burns the attacker."
        ),
        "description_de": (
            "Erleidet das Pokémon durch eine Attacke Schaden, erleidet der "
            "Angreifer Verbrennungen."
        ),
    },
    "eelevate": {
        "name_en": "Eelevate",
        "name_de": "Emporwindung",
        "description_en": (
            "The Pokémon floats off the ground, making it immune to "
            "Ground-type moves, as well as the Spikes, Toxic Spikes, and "
            "Sticky Web statuses. When the Pokémon knocks out a target with "
            "an attack, its highest stat is boosted by 1 stage."
        ),
        "description_de": (
            "Das Pokémon schwebt über dem Boden und ist dadurch immun gegen "
            "Boden-Attacken, Stachler, Giftspitzen und Klebenetz. Besiegt es "
            "ein Pokémon, steigt sein höchster Statuswert um eine Stufe."
        ),
    },
    "fire-mane": {
        "name_en": "Fire Mane",
        "name_de": "Flammenmähne",
        "description_en": (
            "Boosts the power of the Pokémon's Fire-type moves by 50%."
        ),
        "description_de": (
            "Erhöht den Schaden von Feuer-Attacken um 50 %."
        ),
    },
}


def get_json(url: str, attempts: int = 5) -> dict[str, Any]:
    """Fetch JSON with a short retry for temporary API/network failures."""
    request = Request(
        url,
        headers={"User-Agent": "MISHIRO-Pokedex/0.1"},
    )
    for attempt in range(1, attempts + 1):
        try:
            with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                return json.load(response)
        except (HTTPError, URLError, TimeoutError):
            if attempt == attempts:
                raise
            time.sleep(0.5 * attempt)
    raise RuntimeError(f"Could not load {url}")


def clean_api_text(value: object) -> str:
    """Turn PokéAPI formatting and link markup into dialog-friendly text."""
    text = str(value or "").replace("\f", " ").replace("\n", " ")
    text = re.sub(r"\[([^]]+)]\{[^}]+}", r"\1", text)
    return " ".join(text.split())


def localized_name(ability: dict[str, Any], language: str) -> str:
    for entry in ability.get("names", []):
        if entry.get("language", {}).get("name") == language:
            return clean_api_text(entry.get("name"))
    return ""


def localized_short_effect(ability: dict[str, Any], language: str) -> str:
    for entry in ability.get("effect_entries", []):
        if entry.get("language", {}).get("name") == language:
            return clean_api_text(
                entry.get("short_effect") or entry.get("effect")
            )
    return ""


def localized_flavor_text(ability: dict[str, Any], language: str) -> str:
    entries = [
        entry
        for entry in ability.get("flavor_text_entries", [])
        if entry.get("language", {}).get("name") == language
    ]
    if not entries:
        return ""

    by_version_group = {
        entry.get("version_group", {}).get("name"): entry
        for entry in entries
    }
    for version_group in VERSION_GROUP_PRIORITY:
        entry = by_version_group.get(version_group)
        if entry is not None:
            return clean_api_text(entry.get("flavor_text"))
    return clean_api_text(entries[-1].get("flavor_text"))


def normalize_german_description(api_name: str, description: str) -> str:
    """Repair recurring localization errors without removing mechanics."""
    text = clean_api_text(description)
    for old, new in GERMAN_TEXT_REPLACEMENTS:
        text = text.replace(old, new)
    for type_name in GERMAN_ATTACK_TYPE_NAMES:
        text = text.replace(f"{type_name} Attacke", f"{type_name}-Attacke")
    text = re.sub(r"(?<=\d)%", " %", text)
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    if text and text[-1] not in ".!?":
        text += "."
    return PRECISE_GERMAN_DESCRIPTION_OVERRIDES.get(api_name, text)


def build_record(ability: dict[str, Any]) -> dict[str, Any] | None:
    """Normalize one main-series ability for the offline UI catalog."""
    if not ability.get("is_main_series"):
        return None

    api_name = str(ability["name"])
    name_en = localized_name(ability, "en") or api_name.replace("-", " ").title()
    name_de = CURRENT_GERMAN_NAME_OVERRIDES.get(
        api_name,
        localized_name(ability, "de") or name_en,
    )
    description_en = (
        localized_short_effect(ability, "en")
        or localized_flavor_text(ability, "en")
    )
    description_de = normalize_german_description(
        api_name,
        localized_short_effect(ability, "de")
        or GERMAN_DESCRIPTION_FALLBACKS.get(api_name, "")
        or localized_flavor_text(ability, "de")
        or description_en,
    )

    record = {
        "ability_id": int(ability["id"]),
        "api_name": api_name,
        "name_en": name_en,
        "name_de": name_de,
        "description_en": description_en,
        "description_de": description_de,
    }
    record.update(CHAMPIONS_ABILITY_OVERRIDES.get(api_name, {}))
    return record


def write_json_atomically(records: list[dict[str, Any]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f"{output.stem}.tmp{output.suffix}")
    with temporary.open("w", encoding="utf-8") as file:
        json.dump(records, file, ensure_ascii=False, indent=4)
        file.write("\n")
    temporary.replace(output)


def import_abilities(output: Path, workers: int) -> list[dict[str, Any]]:
    index = get_json(f"{API_BASE_URL}/ability?limit=10000&offset=0")
    resources = index.get("results", [])
    records: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(get_json, str(resource["url"])): resource
            for resource in resources
        }
        total = len(futures)
        for position, future in enumerate(as_completed(futures), start=1):
            resource = futures[future]
            ability = future.result()
            record = build_record(ability)
            if record is not None:
                records.append(record)
            print(f"[{position:>3}/{total}] {resource['name']}")

    records.sort(key=lambda record: int(record["ability_id"]))
    write_json_atomically(records, output)
    return records


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Import bilingual main-series ability descriptions from PokéAPI."
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output file (default: data/abilities.json).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=12,
        help="Parallel API requests (default: 12).",
    )
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    if arguments.workers < 1:
        raise ValueError("--workers must be at least 1.")
    records = import_abilities(arguments.output, arguments.workers)
    missing_de = sum(not record["description_de"] for record in records)
    missing_en = sum(not record["description_en"] for record in records)
    print()
    print(f"Importer version: {IMPORTER_VERSION}")
    print(f"Saved {len(records)} abilities to {arguments.output}")
    print(f"Missing descriptions: DE {missing_de}, EN {missing_en}")


if __name__ == "__main__":
    main()