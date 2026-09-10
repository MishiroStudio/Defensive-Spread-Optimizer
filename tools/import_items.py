"""Cordy's Lab item importer — version 6 (import_items.py).

Importer schema version 6.

Build ``data/items.json`` for the Team Builder from PokéAPI.

The catalog contains every held item legal in either Generation VIII,
Generation IX, or one of the Pokémon Champions regulations stored in
``data/regulations.json``. PokéAPI supplies IDs, localized names, descriptions,
categories, attributes and fling data. Pokémon Showdown is the source of truth
for game and regulation legality. Current Champions mods use the exact commit
pinned by ``import_regulations.py``; removed regulation mods use the stable npm
package as an isolated archive runtime.

Run from the project root with:

    python3 tools/import_items.py

A limited test import writes ``data/items_preview.json`` so preview data cannot
overwrite the complete catalog.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

if __package__:
    from tools.item_mechanics import (
        build_item_mechanics,
        validate_item_mechanics,
    )
    from tools.import_moves import (
        load_showdown_commit,
        overlay_live_showdown_mods,
        showdown_snapshot_version,
    )
else:
    from item_mechanics import (  # type: ignore[no-redef]
        build_item_mechanics,
        validate_item_mechanics,
    )
    from import_moves import (  # type: ignore[no-redef]
        load_showdown_commit,
        overlay_live_showdown_mods,
        showdown_snapshot_version,
    )


IMPORTER_VERSION = "v6"
IMPORTER_FILE_VERSION = "import_items.py"
POKEAPI_BASE_URL = "https://pokeapi.co/api/v2"
SHOWDOWN_PACKAGE_METADATA_URL = (
    "https://registry.npmjs.org/pokemon-showdown/latest"
)

PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
DATA_DIRECTORY = PROJECT_DIRECTORY / "data"
REGULATIONS_FILE = DATA_DIRECTORY / "regulations.json"
OUTPUT_FILE = DATA_DIRECTORY / "items.json"
PREVIEW_OUTPUT_FILE = DATA_DIRECTORY / "items_preview.json"

REQUEST_TIMEOUT_SECONDS = 60
MAX_REQUEST_ATTEMPTS = 6
RETRYABLE_HTTP_STATUS_CODES = {429, 500, 502, 503, 504}
USER_AGENT = "Cordys-Lab-Team-Builder/0.3"

GAME_SOURCES = (
    {
        "kind": "game",
        "key": "sword-shield",
        "mod": "gen8",
    },
    {
        "kind": "game",
        "key": "scarlet-violet",
        "mod": "gen9",
    },
)
GAME_KEYS = {source["key"] for source in GAME_SOURCES}
ITEM_CLASSES = {"berry", "held-item", "mega-stone"}

# Shared Team Builder filter categories. An item may deliberately belong to
# several categories, for example Sitrus Berry belongs to both ``healing``
# and ``berries``. Items without a specific category become ``other``.
EFFECT_CATEGORY_ORDER = (
    "stat-boost",
    "power-boost",
    "defense",
    "healing",
    "effect-duration",
    "berries",
    "mega-stones",
    "other",
)

STAT_BOOST_ITEMS = {
    "absorb-bulb",
    "adrenaline-orb",
    "apicot-berry",
    "assault-vest",
    "booster-energy",
    "cell-battery",
    "choice-band",
    "choice-scarf",
    "choice-specs",
    "deep-sea-scale",
    "deep-sea-tooth",
    "electric-seed",
    "eviolite",
    "ganlon-berry",
    "grassy-seed",
    "kee-berry",
    "liechi-berry",
    "light-ball",
    "luminous-moss",
    "maranga-berry",
    "metal-powder",
    "micle-berry",
    "mirror-herb",
    "misty-seed",
    "petaya-berry",
    "psychic-seed",
    "quick-powder",
    "salac-berry",
    "snowball",
    "starf-berry",
    "thick-club",
    "throat-spray",
    "weakness-policy",
    "white-herb",
}

POWER_BOOST_ITEMS = {
    "adamant-crystal",
    "adamant-orb",
    "black-belt",
    "black-glasses",
    "charcoal",
    "cornerstone-mask",
    "draco-plate",
    "dragon-fang",
    "dread-plate",
    "earth-plate",
    "expert-belt",
    "fairy-feather",
    "fist-plate",
    "flame-plate",
    "griseous-core",
    "griseous-orb",
    "hard-stone",
    "hearthflame-mask",
    "icicle-plate",
    "insect-plate",
    "iron-plate",
    "life-orb",
    "loaded-dice",
    "lustrous-globe",
    "lustrous-orb",
    "magnet",
    "meadow-plate",
    "metal-coat",
    "metronome",
    "mind-plate",
    "miracle-seed",
    "muscle-band",
    "mystic-water",
    "never-melt-ice",
    "normal-gem",
    "odd-incense",
    "pixie-plate",
    "poison-barb",
    "punching-glove",
    "rock-incense",
    "rose-incense",
    "sea-incense",
    "sharp-beak",
    "silk-scarf",
    "silver-powder",
    "sky-plate",
    "soft-sand",
    "soul-dew",
    "spell-tag",
    "splash-plate",
    "spooky-plate",
    "stone-plate",
    "toxic-plate",
    "twisted-spoon",
    "wave-incense",
    "wellspring-mask",
    "wise-glasses",
    "zap-plate",
}

DEFENSE_ITEMS = {
    "air-balloon",
    "assault-vest",
    "babiri-berry",
    "bright-powder",
    "charti-berry",
    "chilan-berry",
    "chople-berry",
    "clear-amulet",
    "coba-berry",
    "colbur-berry",
    "covert-cloak",
    "deep-sea-scale",
    "eviolite",
    "focus-band",
    "focus-sash",
    "haban-berry",
    "heavy-duty-boots",
    "kasib-berry",
    "kebia-berry",
    "lax-incense",
    "metal-powder",
    "occa-berry",
    "passho-berry",
    "payapa-berry",
    "protective-pads",
    "rindo-berry",
    "rocky-helmet",
    "roseli-berry",
    "safety-goggles",
    "shed-shell",
    "shuca-berry",
    "tanga-berry",
    "utility-umbrella",
    "wacan-berry",
    "yache-berry",
}

HEALING_ITEMS = {
    "aguav-berry",
    "aspear-berry",
    "berry-juice",
    "big-root",
    "black-sludge",
    "cheri-berry",
    "chesto-berry",
    "enigma-berry",
    "figy-berry",
    "iapapa-berry",
    "leftovers",
    "leppa-berry",
    "lum-berry",
    "mago-berry",
    "mental-herb",
    "oran-berry",
    "pecha-berry",
    "persim-berry",
    "rawst-berry",
    "shell-bell",
    "sitrus-berry",
    "wiki-berry",
}

EFFECT_DURATION_ITEMS = {
    "damp-rock",
    "grip-claw",
    "heat-rock",
    "icy-rock",
    "light-clay",
    "smooth-rock",
    "terrain-extender",
}

# Showdown uses the current English display names for these two items, while
# PokéAPI retains their stable historical resource slugs.
SHOWDOWN_TO_POKEAPI_ALIASES = {
    "leek": "stick",
    "prettyfeather": "pretty-wing",
}

# PokéAPI already contains these items, but currently omits their German names.
# Keep the official German game-localization names here until PokéAPI supplies
# them itself. A PokéAPI translation always takes precedence over this table.
GERMAN_NAME_OVERRIDES = {
    "barbaracite": "Thanathoranit",
    "chandelurite": "Skelabranit",
    "chesnaughtite": "Brigaronit",
    "chimechite": "Palimpalimonit",
    "clefablite": "Pixinit",
    "crabominite": "Krawellonit",
    "delphoxite": "Fennexisnit",
    "dragalgite": "Tandraknit",
    "dragoninite": "Dragoranit",
    "drampanite": "Sen-Longnit",
    "eelektrossite": "Zapplarangonit",
    "emboarite": "Flambirexonit",
    "excadrite": "Stalobornit",
    "falinksite": "Legiosnit",
    "feraligite": "Impergatornit",
    "floettite": "Floetteonit",
    "froslassite": "Frosdedjenit",
    "glimmoranite": "Lumifloranit",
    "golurkite": "Golgantesnit",
    "greninjite": "Quajutsunit",
    "hawluchanite": "Resladeronit",
    "malamarite": "Calamaneronit",
    "meganiumite": "Meganienit",
    "meowsticite": "Psiaugonit",
    "pyroarite": "Pyroleonit",
    "raichunite-x": "Raichunit X",
    "raichunite-y": "Raichunit Y",
    "roseli-berry": "Hibisbeere",
    "scovillainite": "Halupenjonit",
    "scraftinite": "Irokexonit",
    "scolipite": "Cerapendranit",
    "skarmorite": "Panzaeronit",
    "staraptite": "Staraptornit",
    "starminite": "Starmienit",
    "victreebelite": "Sarzenianit",
}

# PokéAPI currently omits German descriptions for these newer items. These
# concise descriptions state the battle or evolution effect directly so the
# same text remains useful in the Team Builder and later calculators.
GERMAN_DESCRIPTION_OVERRIDES = {
    "ability-shield": (
        "Die Fähigkeit des Trägers kann weder verändert noch unterdrückt "
        "oder ignoriert werden."
    ),
    "adamant-crystal": (
        "Wird dieses Item von Dialga getragen, verstärkt es dessen Attacken "
        "vom Typ Stahl und Drache um 20 %."
    ),
    "auspicious-armor": (
        "Entwickelt Knarbon bei Anwendung zu Crimanzo."
    ),
    "booster-energy": (
        "Aktiviert die Fähigkeit Paläosynthese oder Quantenantrieb. Wird "
        "dabei verbraucht."
    ),
    "clear-amulet": (
        "Verhindert, dass andere Pokémon die Statuswerte des Trägers senken."
    ),
    "cornerstone-mask": (
        "Verstärkt die Attacken von Fundamentmasken-Ogerpon um 20 % und "
        "ermöglicht bei der Terakristallisierung Erinnerungskraft."
    ),
    "covert-cloak": (
        "Schützt den Träger vor Zusatzeffekten gegnerischer Attacken."
    ),
    "fairy-feather": (
        "Verstärkt Attacken vom Typ Fee des Trägers um 20 %."
    ),
    "griseous-core": (
        "Wird dieses Item von Giratina getragen, verstärkt es dessen "
        "Attacken vom Typ Geist und Drache um 20 %."
    ),
    "hearthflame-mask": (
        "Verstärkt die Attacken von Ofenmasken-Ogerpon um 20 % und "
        "ermöglicht bei der Terakristallisierung Erinnerungskraft."
    ),
    "loaded-dice": (
        "Attacken des Trägers, die normalerweise zwei- bis fünfmal treffen, "
        "treffen vier- bis fünfmal. Mäuseplage trifft vier- bis zehnmal."
    ),
    "lustrous-globe": (
        "Wird dieses Item von Palkia getragen, verstärkt es dessen Attacken "
        "vom Typ Wasser und Drache um 20 %."
    ),
    "malicious-armor": (
        "Entwickelt Knarbon bei Anwendung zu Azugladis."
    ),
    "masterpiece-teacup": (
        "Entwickelt ein kompatibles Mortcha bei Anwendung zu Fatalitcha."
    ),
    "metal-alloy": (
        "Entwickelt Duraludon bei Anwendung zu Briduradon."
    ),
    "mirror-herb": (
        "Erhöht ein gegnerisches Pokémon seine Statuswerte, übernimmt der "
        "Träger einmalig dieselben Erhöhungen. Wird dabei verbraucht."
    ),
    "punching-glove": (
        "Verstärkt Box- und Faust-Attacken des Trägers um 10 % und "
        "verhindert dabei direkten Kontakt."
    ),
    "roseli-berry": (
        "Als getragenes Item schwächt diese Beere sehr effektive "
        "gegnerische Attacken vom Typ Fee."
    ),
    "syrupy-apple": (
        "Entwickelt Knapfel bei Anwendung zu Sirapfel."
    ),
    "unremarkable-teacup": (
        "Entwickelt ein kompatibles Mortcha bei Anwendung zu Fatalitcha."
    ),
    "wellspring-mask": (
        "Verstärkt die Attacken von Brunnenmasken-Ogerpon um 20 % und "
        "ermöglicht bei der Terakristallisierung Erinnerungskraft."
    ),
}

# German holder names are kept separately because Mega Stone names cannot be
# derived safely from English Pokémon names (for example Chandelure/Skelabra).
GERMAN_MEGA_STONE_HOLDERS = {
    "barbaracite": "Thanathora",
    "chandelurite": "Skelabra",
    "chesnaughtite": "Brigaron",
    "chimechite": "Palimpalim",
    "clefablite": "Pixi",
    "crabominite": "Krawell",
    "delphoxite": "Fennexis",
    "dragalgite": "Tandrak",
    "dragoninite": "Dragoran",
    "drampanite": "Sen-Long",
    "eelektrossite": "Zapplarang",
    "emboarite": "Flambirex",
    "excadrite": "Stalobor",
    "falinksite": "Legios",
    "feraligite": "Impergator",
    "floettite": "Ewigblütler-Floette",
    "froslassite": "Frosdedje",
    "glimmoranite": "Lumiflora",
    "golurkite": "Golgantes",
    "greninjite": "Quajutsu",
    "hawluchanite": "Resladero",
    "malamarite": "Calamanero",
    "meganiumite": "Meganie",
    "meowsticite": "Psiaugon",
    "pyroarite": "Pyroleo",
    "raichunite-x": "Raichu",
    "raichunite-y": "Raichu",
    "scovillainite": "Halupenjo",
    "scraftinite": "Irokex",
    "scolipite": "Cerapendra",
    "skarmorite": "Panzaeron",
    "staraptite": "Staraptor",
    "starminite": "Starmie",
    "victreebelite": "Sarzenia",
}


def german_description_override(api_name: str) -> str:
    """Return a curated German description missing from PokéAPI."""
    description = GERMAN_DESCRIPTION_OVERRIDES.get(api_name)
    if description:
        return description

    holder_name = GERMAN_MEGA_STONE_HOLDERS.get(api_name)
    if holder_name:
        return (
            "Einer der mysteriösen Mega-Steine. Wird er von einem "
            f"{holder_name} getragen, kann es im Kampf eine "
            "Mega-Entwicklung durchführen."
        )

    return ""


def build_item_effect_categories(item: dict[str, Any]) -> list[str]:
    """Return the stored Team Builder categories for one item."""
    api_name = str(item["api_name"])
    categories: set[str] = set()

    if api_name in STAT_BOOST_ITEMS:
        categories.add("stat-boost")
    if api_name in POWER_BOOST_ITEMS:
        categories.add("power-boost")
    if api_name in DEFENSE_ITEMS:
        categories.add("defense")
    if api_name in HEALING_ITEMS:
        categories.add("healing")
    if api_name in EFFECT_DURATION_ITEMS:
        categories.add("effect-duration")
    if item.get("item_class") == "berry":
        categories.add("berries")
    if item.get("item_class") == "mega-stone" or item.get("mega_stone"):
        categories.add("mega-stones")
    if not categories:
        categories.add("other")

    return [
        category
        for category in EFFECT_CATEGORY_ORDER
        if category in categories
    ]


def validate_item_effect_categories(
    categories: object,
    item_name: str,
) -> None:
    """Reject missing, duplicate, unknown, or unsorted categories."""
    if not isinstance(categories, list) or not categories:
        raise ValueError(f"Missing effect_categories for {item_name}")
    if any(not isinstance(category, str) for category in categories):
        raise ValueError(f"Invalid effect_categories for {item_name}")
    if len(categories) != len(set(categories)):
        raise ValueError(f"Duplicate effect_categories for {item_name}")
    if not set(categories).issubset(EFFECT_CATEGORY_ORDER):
        raise ValueError(f"Unknown effect_categories for {item_name}")
    if "other" in categories and len(categories) != 1:
        raise ValueError(f"Contradictory effect_categories for {item_name}")

    expected_order = [
        category
        for category in EFFECT_CATEGORY_ORDER
        if category in categories
    ]
    if categories != expected_order:
        raise ValueError(f"Unsorted effect_categories for {item_name}")


NODE_EXPORT_SCRIPT = r"""
const path = require('path');

const packageDirectory = process.argv[1];
const sources = JSON.parse(process.argv[2]);
const {Dex} = require(path.join(packageDirectory, 'dist', 'sim', 'dex'));

function toId(value) {
  return String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, '');
}

function normalizeMegaStone(value) {
  if (!value) return {};
  if (typeof value === 'string') return {result: toId(value)};
  if (typeof value !== 'object' || Array.isArray(value)) return {};
  return Object.fromEntries(
    Object.entries(value).map(([base, result]) => [toId(base), toId(result)])
  );
}

function itemClass(item) {
  if (item.megaStone) return 'mega-stone';
  if (item.isBerry) return 'berry';
  return 'held-item';
}

function createRecord(item, source) {
  const callbackFields = Object.entries(item)
    .filter(([, value]) => typeof value === 'function')
    .map(([key]) => key)
    .sort();

  return {
    showdown_id: item.id,
    showdown_num: item.num,
    showdown_name: item.name,
    showdown_description_en: item.shortDesc || item.desc || '',
    mechanics_source_key: source.key,
    mechanics_source_mod: source.mod,
    item_class: itemClass(item),
    showdown_fling_power: item.fling && item.fling.basePower != null
      ? item.fling.basePower
      : null,
    restricted_to: (item.itemUser || []).map(toId).sort(),
    mega_stone: normalizeMegaStone(item.megaStone),
    is_choice_item: Boolean(item.isChoice),
    has_custom_logic: callbackFields.length > 0,
    callback_fields: callbackFields,
    legal_in_games: [],
    legal_in_regulations: [],
  };
}

function mergeRecord(record, item) {
  if (record.showdown_num !== item.num) {
    throw new Error(
      `Showdown number mismatch for ${item.id}: ` +
      `${record.showdown_num} and ${item.num}`
    );
  }

  record.restricted_to = [...new Set([
    ...record.restricted_to,
    ...(item.itemUser || []).map(toId),
  ])].sort();
  record.mega_stone = {
    ...record.mega_stone,
    ...normalizeMegaStone(item.megaStone),
  };
  record.is_choice_item ||= Boolean(item.isChoice);

  const callbackFields = Object.entries(item)
    .filter(([, value]) => typeof value === 'function')
    .map(([key]) => key);
  record.callback_fields = [...new Set([
    ...record.callback_fields,
    ...callbackFields,
  ])].sort();
  record.has_custom_logic = record.callback_fields.length > 0;
}

const itemsById = new Map();

for (const source of sources) {
  let dex;
  try {
    dex = Dex.mod(source.mod);
  } catch (error) {
    throw new Error(
      `Showdown mod ${source.mod} for ${source.key} is unavailable in ` +
      `${packageDirectory}: ${error.message}`
    );
  }

  for (const item of dex.items.all()) {
    if (
      !item.exists ||
      item.isNonstandard ||
      item.num <= 0 ||
      item.isPokeball
    ) continue;

    let record = itemsById.get(item.id);
    if (!record) {
      record = createRecord(item, source);
      itemsById.set(item.id, record);
    } else {
      mergeRecord(record, item);
    }

    const target = source.kind === 'regulation'
      ? record.legal_in_regulations
      : record.legal_in_games;
    if (!target.includes(source.key)) target.push(source.key);
  }
}

const items = [...itemsById.values()].sort(
  (left, right) => left.showdown_id.localeCompare(right.showdown_id)
);

process.stdout.write(JSON.stringify(items));
"""


def get_bytes(url: str) -> bytes:
    """Download bytes with retries for temporary network failures."""
    request = Request(url, headers={"User-Agent": USER_AGENT})

    for attempt in range(MAX_REQUEST_ATTEMPTS):
        try:
            with urlopen(
                request,
                timeout=REQUEST_TIMEOUT_SECONDS,
            ) as response:
                return response.read()
        except HTTPError as error:
            should_retry = (
                error.code in RETRYABLE_HTTP_STATUS_CODES
                and attempt < MAX_REQUEST_ATTEMPTS - 1
            )
            if not should_retry:
                raise
        except (URLError, TimeoutError):
            if attempt >= MAX_REQUEST_ATTEMPTS - 1:
                raise

        time.sleep(0.5 * (2**attempt))

    raise RuntimeError(f"Could not download {url}")


@lru_cache(maxsize=None)
def get_json(url: str) -> dict[str, Any]:
    """Load and cache one JSON resource."""
    return json.loads(get_bytes(url).decode("utf-8"))


def load_json(path: Path) -> Any:
    if not path.is_file():
        raise FileNotFoundError(f"Missing data file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {path}: {error}") from error


def load_regulation_sources(path: Path) -> list[dict[str, str]]:
    """Return Showdown source definitions from regulations.json."""
    data = load_json(path)
    if not isinstance(data, dict):
        raise ValueError("regulations.json must contain a JSON object.")

    records = data.get("regulations")
    if not isinstance(records, list) or not records:
        raise ValueError(
            "regulations.json must contain a non-empty regulations list."
        )

    sources: list[dict[str, str]] = []
    regulation_ids: set[str] = set()

    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Every regulation must be a JSON object.")
        regulation_id = str(record.get("id", "")).strip()
        mod = str(record.get("mod", "")).strip()
        if not regulation_id or not mod:
            raise ValueError("Every regulation needs an id and Showdown mod.")
        if regulation_id in regulation_ids:
            raise ValueError(f"Duplicate regulation id: {regulation_id}")

        regulation_ids.add(regulation_id)
        sources.append(
            {
                "kind": "regulation",
                "key": regulation_id,
                "mod": mod,
            }
        )

    return sources


def require_node() -> str:
    """Return the Node.js executable required by Showdown's Dex loader."""
    node_executable = shutil.which("node")
    if node_executable is None:
        raise RuntimeError(
            "Node.js was not found. Install Node.js before running the "
            "item importer; Showdown's own Dex loader requires it."
        )
    return node_executable


def download_showdown_package() -> tuple[bytes, str]:
    """Download the latest stable Pokémon Showdown npm package."""
    print("Loading Pokémon Showdown package metadata...")
    metadata = get_json(SHOWDOWN_PACKAGE_METADATA_URL)
    version = str(metadata["version"])
    tarball_url = str(metadata["dist"]["tarball"])

    print(f"Downloading Pokémon Showdown {version}...")
    return get_bytes(tarball_url), version


def extract_showdown_dist(tarball: bytes, destination: Path) -> Path:
    """Safely extract only Showdown's compiled runtime files."""
    destination = destination.resolve()

    with tarfile.open(fileobj=io.BytesIO(tarball), mode="r:gz") as archive:
        members = [
            member
            for member in archive.getmembers()
            if member.name.startswith("package/dist/")
        ]
        if not members:
            raise RuntimeError(
                "The Showdown package does not contain compiled data."
            )

        for member in members:
            if member.issym() or member.islnk():
                raise RuntimeError(
                    f"Refusing link in Showdown package: {member.name}"
                )

            target = (destination / member.name).resolve()
            try:
                target.relative_to(destination)
            except ValueError as error:
                raise RuntimeError(
                    f"Unsafe path in Showdown package: {member.name}"
                ) from error

        archive.extractall(destination, members=members, filter="data")

    return destination / "package"


def export_items(
    showdown_package: Path,
    node_executable: str,
    sources: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """Return the union of game- and regulation-legal held items."""
    try:
        result = subprocess.run(
            [
                node_executable,
                "-e",
                NODE_EXPORT_SCRIPT,
                str(showdown_package),
                json.dumps(sources),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as error:
        details = error.stderr.strip() or "No Node.js error output."
        raise RuntimeError(
            f"Showdown item export failed:\n{details}"
        ) from error

    try:
        items = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("Showdown returned invalid item JSON.") from error

    if not isinstance(items, list):
        raise RuntimeError("Showdown did not return an item list.")
    return items


def merge_showdown_item_exports(
    *exports: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge isolated live/archive exports, preserving live mechanics.

    The first export has priority for descriptions and mechanics metadata.
    Legality and collection-valued mechanics are combined across runtimes.
    """
    items_by_id: dict[str, dict[str, Any]] = {}

    for exported_items in exports:
        for incoming in exported_items:
            showdown_id = str(incoming.get("showdown_id", ""))
            if not showdown_id:
                raise ValueError("Showdown returned an item without an ID.")

            existing = items_by_id.get(showdown_id)
            if existing is None:
                items_by_id[showdown_id] = {
                    **incoming,
                    "restricted_to": list(incoming["restricted_to"]),
                    "mega_stone": dict(incoming["mega_stone"]),
                    "callback_fields": list(incoming["callback_fields"]),
                    "legal_in_games": list(incoming["legal_in_games"]),
                    "legal_in_regulations": list(
                        incoming["legal_in_regulations"]
                    ),
                }
                continue

            if existing["showdown_num"] != incoming["showdown_num"]:
                raise ValueError(
                    "Showdown number mismatch across live/archive data for "
                    f"{showdown_id}: {existing['showdown_num']} and "
                    f"{incoming['showdown_num']}"
                )

            for key in (
                "restricted_to",
                "callback_fields",
                "legal_in_games",
                "legal_in_regulations",
            ):
                existing[key] = sorted(
                    set(existing[key]) | set(incoming[key])
                )

            existing["mega_stone"] = {
                **incoming["mega_stone"],
                **existing["mega_stone"],
            }
            existing["is_choice_item"] = bool(
                existing["is_choice_item"]
                or incoming["is_choice_item"]
            )
            existing["has_custom_logic"] = bool(
                existing["callback_fields"]
            )
            if not existing["showdown_description_en"]:
                existing["showdown_description_en"] = incoming[
                    "showdown_description_en"
                ]
            if existing["showdown_fling_power"] is None:
                existing["showdown_fling_power"] = incoming[
                    "showdown_fling_power"
                ]

    return sorted(
        items_by_id.values(),
        key=lambda item: str(item["showdown_id"]),
    )


def to_showdown_id(value: str) -> str:
    """Normalize a PokéAPI slug like Showdown's toID()."""
    normalized = unicodedata.normalize("NFKD", value).casefold()
    normalized = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9]", "", normalized)


def clean_api_text(value: object) -> str:
    """Collapse PokéAPI line breaks and formatting whitespace."""
    return " ".join(
        str(value or "").replace("\f", " ").replace("\n", " ").split()
    )


def localized_name(item: dict[str, Any], language: str) -> str:
    for entry in item.get("names", []):
        if entry.get("language", {}).get("name") == language:
            return clean_api_text(entry.get("name"))
    return ""


def localized_short_effect(item: dict[str, Any], language: str) -> str:
    for entry in item.get("effect_entries", []):
        if entry.get("language", {}).get("name") == language:
            return clean_api_text(
                entry.get("short_effect") or entry.get("effect")
            )
    return ""


def latest_flavor_text(item: dict[str, Any], language: str) -> str:
    entries = [
        entry
        for entry in item.get("flavor_text_entries", [])
        if entry.get("language", {}).get("name") == language
    ]
    for entry in reversed(entries):
        text = clean_api_text(entry.get("text"))
        if text:
            return text
    return ""


def apply_pokeapi_data(
    showdown_item: dict[str, Any],
    api_item: dict[str, Any],
) -> dict[str, Any]:
    """Create one final catalog record from PokéAPI and legality data."""
    api_name = str(api_item.get("name", ""))
    showdown_id = str(showdown_item["showdown_id"])
    expected_api_name = SHOWDOWN_TO_POKEAPI_ALIASES.get(showdown_id)
    names_match = (
        api_name == expected_api_name
        if expected_api_name is not None
        else to_showdown_id(api_name) == showdown_id
    )
    if not names_match:
        raise ValueError(
            f"PokéAPI item {api_name!r} does not match "
            f"Showdown item {showdown_id!r}."
        )

    name_en = localized_name(api_item, "en") or showdown_item["showdown_name"]
    name_de = (
        localized_name(api_item, "de")
        or GERMAN_NAME_OVERRIDES.get(api_name, "")
    )
    description_en = (
        localized_short_effect(api_item, "en")
        or latest_flavor_text(api_item, "en")
        or showdown_item["showdown_description_en"]
    )
    description_de = (
        localized_short_effect(api_item, "de")
        or latest_flavor_text(api_item, "de")
        or german_description_override(api_name)
    )

    fling_effect = api_item.get("fling_effect")
    if isinstance(fling_effect, dict):
        fling_effect = fling_effect.get("name")
    else:
        fling_effect = None

    category = api_item.get("category")
    category_name = (
        str(category.get("name")) if isinstance(category, dict) else ""
    )
    attributes = sorted(
        str(attribute.get("name"))
        for attribute in api_item.get("attributes", [])
        if isinstance(attribute, dict) and attribute.get("name")
    )

    record = {
        "item_id": int(api_item["id"]),
        "api_name": api_name,
        "showdown_id": showdown_id,
        "showdown_num": int(showdown_item["showdown_num"]),
        "name_en": name_en,
        "name_de": name_de or name_en,
        "name_de_is_fallback": not bool(name_de),
        "description_en": description_en,
        "description_de": description_de or description_en,
        "description_de_is_fallback": not bool(description_de),
        "category": category_name,
        "item_class": showdown_item["item_class"],
        "attributes": attributes,
        "fling_power": (
            api_item.get("fling_power")
            if api_item.get("fling_power") is not None
            else showdown_item["showdown_fling_power"]
        ),
        "fling_effect": fling_effect,
        "restricted_to": showdown_item["restricted_to"],
        "mega_stone": showdown_item["mega_stone"],
        "is_choice_item": showdown_item["is_choice_item"],
        "has_custom_logic": showdown_item["has_custom_logic"],
        "callback_fields": showdown_item["callback_fields"],
        "legal_in_games": showdown_item["legal_in_games"],
        "legal_in_regulations": showdown_item["legal_in_regulations"],
    }
    record["mechanics"] = build_item_mechanics(
        {
            **record,
            "showdown_description_en": showdown_item[
                "showdown_description_en"
            ],
            "mechanics_source_key": showdown_item[
                "mechanics_source_key"
            ],
            "mechanics_source_mod": showdown_item[
                "mechanics_source_mod"
            ],
        }
    )
    record["effect_categories"] = build_item_effect_categories(record)
    return record


def build_pokeapi_item_index() -> dict[str, dict[str, str]]:
    """Index every PokéAPI item resource by normalized Showdown ID."""
    index = get_json(f"{POKEAPI_BASE_URL}/item?limit=10000&offset=0")
    resources = index.get("results", [])
    result: dict[str, dict[str, str]] = {}

    for resource in resources:
        api_name = str(resource.get("name", ""))
        url = str(resource.get("url", ""))
        if not api_name or not url:
            continue
        result[to_showdown_id(api_name)] = {
            "name": api_name,
            "url": url,
        }

    for showdown_id, api_name in SHOWDOWN_TO_POKEAPI_ALIASES.items():
        api_resource = result.get(to_showdown_id(api_name))
        if api_resource is None:
            raise ValueError(
                f"PokéAPI alias target is missing: {api_name}"
            )
        result[showdown_id] = api_resource

    return result


def fetch_pokeapi_records(
    items: list[dict[str, Any]],
    *,
    workers: int,
) -> list[dict[str, Any]]:
    """Download and merge all required PokéAPI item resources."""
    resources = build_pokeapi_item_index()
    missing = [
        str(item["showdown_id"])
        for item in items
        if str(item["showdown_id"]) not in resources
    ]
    if missing:
        raise ValueError(
            "PokéAPI has no matching records for: " + ", ".join(missing)
        )

    records: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                get_json,
                resources[str(item["showdown_id"])]["url"],
            ): item
            for item in items
        }
        total = len(futures)
        for position, future in enumerate(as_completed(futures), start=1):
            showdown_item = futures[future]
            record = apply_pokeapi_data(showdown_item, future.result())
            records.append(record)
            print(f"[{position:>3}/{total}] {record['api_name']}")

    records.sort(key=lambda record: int(record["item_id"]))
    return records


def validate_items(
    items: list[dict[str, Any]],
    regulation_ids: set[str],
) -> None:
    """Reject duplicate, incomplete or invalid catalog records."""
    item_ids: set[int] = set()
    api_names: set[str] = set()
    showdown_ids: set[str] = set()

    for item in items:
        item_id = item.get("item_id")
        api_name = item.get("api_name")
        showdown_id = item.get("showdown_id")

        if not isinstance(item_id, int) or item_id < 1:
            raise ValueError("Every item needs a positive PokéAPI item_id.")
        if not isinstance(api_name, str) or not api_name:
            raise ValueError(f"Missing api_name for item {item_id}")
        if not isinstance(showdown_id, str) or not showdown_id:
            raise ValueError(f"Missing showdown_id for item {item_id}")

        if item_id in item_ids:
            raise ValueError(f"Duplicate item_id: {item_id}")
        if api_name in api_names:
            raise ValueError(f"Duplicate api_name: {api_name}")
        if showdown_id in showdown_ids:
            raise ValueError(f"Duplicate showdown_id: {showdown_id}")

        for key in (
            "name_en",
            "name_de",
            "description_en",
            "description_de",
            "category",
        ):
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise ValueError(f"Missing {key} for {api_name}")

        for key in (
            "name_de_is_fallback",
            "description_de_is_fallback",
            "is_choice_item",
            "has_custom_logic",
        ):
            if not isinstance(item.get(key), bool):
                raise ValueError(f"Invalid {key} for {api_name}")

        if item.get("item_class") not in ITEM_CLASSES:
            raise ValueError(f"Invalid item_class for {api_name}")

        validate_item_mechanics(item.get("mechanics"), api_name)
        validate_item_effect_categories(
            item.get("effect_categories"),
            api_name,
        )

        legal_games = item.get("legal_in_games")
        legal_regulations = item.get("legal_in_regulations")
        if not isinstance(legal_games, list) or not isinstance(
            legal_regulations,
            list,
        ):
            raise ValueError(f"Missing legality lists for {api_name}")
        if len(legal_games) != len(set(legal_games)):
            raise ValueError(f"Duplicate game legality for {api_name}")
        if len(legal_regulations) != len(set(legal_regulations)):
            raise ValueError(f"Duplicate regulation legality for {api_name}")
        if not set(legal_games).issubset(GAME_KEYS):
            raise ValueError(f"Unknown game legality for {api_name}")
        if not set(legal_regulations).issubset(regulation_ids):
            raise ValueError(f"Unknown regulation legality for {api_name}")
        if not legal_games and not legal_regulations:
            raise ValueError(f"Item has no legal source: {api_name}")

        item_ids.add(item_id)
        api_names.add(api_name)
        showdown_ids.add(showdown_id)


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


def import_items(
    *,
    limit: int | None = None,
    workers: int = 12,
) -> tuple[Path, list[dict[str, Any]], str]:
    """Build, localize, validate and write the full item catalog."""
    if limit is not None and limit < 1:
        raise ValueError("--limit must be at least 1.")
    if workers < 1:
        raise ValueError("--workers must be at least 1.")

    regulation_sources = load_regulation_sources(REGULATIONS_FILE)
    regulation_ids = {source["key"] for source in regulation_sources}

    node_executable = require_node()
    showdown_commit = load_showdown_commit(REGULATIONS_FILE)
    tarball, npm_version = download_showdown_package()
    showdown_version = showdown_snapshot_version(
        npm_version,
        showdown_commit,
    )

    with tempfile.TemporaryDirectory(
        prefix="cordys-showdown-"
    ) as temporary_directory:
        temporary_root = Path(temporary_directory)
        live_package = extract_showdown_dist(
            tarball,
            temporary_root / "live",
        )

        regulation_mods = {
            str(source["mod"])
            for source in regulation_sources
        }
        live_mods = overlay_live_showdown_mods(
            live_package,
            showdown_commit,
            regulation_mods | {"champions"},
            required_mods={"champions"},
        )
        live_regulation_sources = [
            source
            for source in regulation_sources
            if source["mod"] in live_mods
        ]
        archive_regulation_sources = [
            source
            for source in regulation_sources
            if source["mod"] not in live_mods
        ]

        live_items = export_items(
            live_package,
            node_executable,
            [*live_regulation_sources, *GAME_SOURCES],
        )

        archive_items: list[dict[str, Any]] = []
        if archive_regulation_sources:
            print(
                "Loading archived Showdown regulation mod(s) from npm: "
                + ", ".join(
                    str(source["mod"])
                    for source in archive_regulation_sources
                )
            )
            archive_package = extract_showdown_dist(
                tarball,
                temporary_root / "archive",
            )
            try:
                archive_items = export_items(
                    archive_package,
                    node_executable,
                    archive_regulation_sources,
                )
            except RuntimeError as error:
                archived_mods = ", ".join(
                    str(source["mod"])
                    for source in archive_regulation_sources
                )
                raise RuntimeError(
                    "Archived regulation data is absent from both the "
                    "pinned Showdown commit and the stable npm package "
                    f"({archived_mods}). Preserve the last generated item "
                    "snapshot or configure another archive source."
                ) from error

        showdown_items = merge_showdown_item_exports(
            live_items,
            archive_items,
        )

    if limit is not None:
        showdown_items = showdown_items[:limit]

    items = fetch_pokeapi_records(showdown_items, workers=workers)
    for item in items:
        item["source"] = {
            "database": "pokeapi",
            "legality_database": "pokemon-showdown",
            "showdown_version": showdown_version,
            "showdown_npm_version": npm_version,
            "showdown_commit": showdown_commit,
        }

    validate_items(items, regulation_ids)

    output_file = PREVIEW_OUTPUT_FILE if limit is not None else OUTPUT_FILE
    write_json_atomically(items, output_file)
    return output_file, items, showdown_version


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Import the PokéAPI catalog for held items legal in "
            "Generation VIII, Generation IX or a Champions regulation."
        )
    )
    parser.add_argument(
        "--limit",
        type=int,
        help=(
            "Import only the first N items and write items_preview.json."
        ),
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=12,
        help="Parallel PokéAPI requests (default: 12).",
    )
    return parser.parse_args()


def main() -> None:
    print(
        f"Cordy's Lab item importer {IMPORTER_VERSION} "
        f"({IMPORTER_FILE_VERSION})"
    )
    arguments = parse_arguments()
    output_file, items, showdown_version = import_items(
        limit=arguments.limit,
        workers=arguments.workers,
    )

    game_counts = {
        game: sum(game in item["legal_in_games"] for item in items)
        for game in sorted(GAME_KEYS)
    }
    regulation_counts: dict[str, int] = {}
    for item in items:
        for regulation_id in item["legal_in_regulations"]:
            regulation_counts[regulation_id] = (
                regulation_counts.get(regulation_id, 0) + 1
            )

    name_fallbacks = sum(item["name_de_is_fallback"] for item in items)
    description_fallbacks = sum(
        item["description_de_is_fallback"] for item in items
    )

    print()
    print(
        f"Done! Imported {len(items)} PokéAPI items with legality from "
        f"Pokémon Showdown {showdown_version}."
    )
    for game, count in game_counts.items():
        print(f"{game}: {count}")
    for regulation_id, count in sorted(regulation_counts.items()):
        print(f"{regulation_id}: {count}")
    print(f"German-name fallbacks: {name_fallbacks}")
    print(f"German-description fallbacks: {description_fallbacks}")
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    main()
