"""Cordy's Lab learnset importer — version 4 (import_learnset.py).

Build the learnset database used by the Cordy's Lab Pokédex.

Every mechanically distinct form from ``data/pokemon_v2.json`` receives
exactly one record.

For Pokémon legal in the current Pokémon Champions regulation, the importer
uses only the Pokémon Champions movepool. It never falls back to
Scarlet/Violet, Sword/Shield or BDSP for those Pokémon. This is important
because Champions can remove moves that exist in the main-series games.

For Pokémon that are not legal in the current Champions regulation, learnsets
use this fallback priority:

1. Scarlet/Violet
2. Sword/Shield
3. Brilliant Diamond/Shining Pearl

Legends games and generations before Generation 8 are deliberately excluded.
If none of the selected games contains the form, the importer stores an empty
movepool and the note ``No set is currently available.``

Pokémon Champions movepools are resolved with Pokémon Showdown's
``Dex.species.getMovePool()``, which returns the complete valid movepool for
the current generation/mod. The fallback games retain the existing
generation-filtered learnset logic.

Version 4 also determines ``available_in_champions`` from the current
regulation in ``data/regulations.json`` instead of inferring availability from
the existence of a Champions learnset entry.

The Champions data is pinned to the exact Pokémon Showdown commit written by
``import_regulations.py``. The stable npm runtime continues to provide the
base game data, while the live Champions mod is overlaid from that commit.

Run from the project root with:

    python3 tools/import_learnset.py

The normal import writes ``data/learnsets.json``. A limited test import writes
``data/learnsets_preview.json`` so preview data can never replace the complete
file.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from import_moves import (
        download_showdown_package,
        extract_showdown_dist,
        load_showdown_commit,
        overlay_live_showdown_mods,
        require_node,
        showdown_snapshot_version,
        write_json_atomically,
    )
except ModuleNotFoundError:
    # Supports ``python -m tools.import_learnset`` as well as executing the
    # file directly with ``python tools/import_learnset.py``.
    from tools.import_moves import (
        download_showdown_package,
        extract_showdown_dist,
        load_showdown_commit,
        overlay_live_showdown_mods,
        require_node,
        showdown_snapshot_version,
        write_json_atomically,
    )


PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
DATA_DIRECTORY = PROJECT_DIRECTORY / "data"
POKEMON_FILE = DATA_DIRECTORY / "pokemon_v2.json"
MOVES_FILE = DATA_DIRECTORY / "moves.json"
REGULATIONS_FILE = DATA_DIRECTORY / "regulations.json"
OUTPUT_FILE = DATA_DIRECTORY / "learnsets.json"
PREVIEW_OUTPUT_FILE = DATA_DIRECTORY / "learnsets_preview.json"

NO_CURRENT_LEARNSET_NOTE = "No set is currently available."

# Champions is handled specially: current-regulation Pokémon MUST use the
# Champions movepool and may never fall back to another game.
CHAMPIONS_SOURCE = {
    "key": "champions",
    "showdown_mod": "champions",
    "label": "Pokémon Champions",
    "generation": 9,
    "is_fallback": False,
}

FALLBACK_LEARNSET_SOURCES = (
    {
        "key": "scarlet-violet",
        "showdown_mod": "gen9",
        "label": "Scarlet/Violet",
        "generation": 9,
        "is_fallback": True,
    },
    {
        "key": "sword-shield",
        "showdown_mod": "gen8",
        "label": "Sword/Shield",
        "generation": 8,
        "is_fallback": True,
    },
    {
        "key": "bdsp",
        "showdown_mod": "gen8bdsp",
        "label": "Brilliant Diamond/Shining Pearl",
        "generation": 8,
        "is_fallback": True,
    },
)

LEARNSET_SOURCES = (CHAMPIONS_SOURCE, *FALLBACK_LEARNSET_SOURCES)
SOURCE_BY_KEY = {source["key"]: source for source in LEARNSET_SOURCES}


# Most PokéAPI names become Showdown IDs simply by removing punctuation.
# These are the exceptional names for mechanically distinct forms retained by
# pokemon_v2.json. Multiple candidates are ordered from most specific to most
# general and are checked only when that species really exists in the selected
# Showdown source.
SHOWDOWN_ID_ALIASES: dict[str, tuple[str, ...]] = {
    "aegislash-shield": ("aegislash",),
    "basculin-red-striped": ("basculin",),
    "basculegion-female": ("basculegionf",),
    "basculegion-male": ("basculegion",),
    "darmanitan-galar-standard": ("darmanitangalar",),
    "darmanitan-standard": ("darmanitan",),
    "deoxys-normal": ("deoxys",),
    "dudunsparce-three-segment": ("dudunsparcethreesegment",),
    "dudunsparce-two-segment": ("dudunsparce",),
    "eiscue-ice": ("eiscue",),
    "enamorus-incarnate": ("enamorus",),
    "giratina-altered": ("giratina",),
    "gourgeist-average": ("gourgeist",),
    "frillish-male": ("frillish",),
    "indeedee-female": ("indeedeef",),
    "indeedee-male": ("indeedee",),
    "keldeo-ordinary": ("keldeo",),
    "koraidon-limited-build": ("koraidon",),
    "landorus-incarnate": ("landorus",),
    "lycanroc-midday": ("lycanroc",),
    "maushold-family-of-four": ("maushold", "mausholdfour"),
    "maushold-family-of-three": ("mausholdthree",),
    "meloetta-aria": ("meloetta",),
    "meowstic-female": ("meowsticf",),
    "meowstic-female-mega": ("meowsticfmega",),
    "meowstic-male": ("meowstic",),
    "meowstic-male-mega": ("meowsticmmega",),
    "mimikyu-disguised": ("mimikyu",),
    "minior-red": ("minior", "miniorred"),
    "minior-red-meteor": ("miniormeteor", "minior"),
    "miraidon-low-power-mode": ("miraidon",),
    "morpeko-full-belly": ("morpeko",),
    "oinkologne-female": ("oinkolognef",),
    "oinkologne-male": ("oinkologne",),
    "oricorio-baile": ("oricorio",),
    "palafin-zero": ("palafin",),
    "poltchageist-counterfeit": ("poltchageist",),
    "pumpkaboo-average": ("pumpkaboo",),
    "pyroar-male": ("pyroar",),
    "rockruff-own-tempo": ("rockruffdusk",),
    "shaymin-land": ("shaymin",),
    "sinistcha-unremarkable": ("sinistcha",),
    "squawkabilly-blue-plumage": ("squawkabillyblue",),
    "squawkabilly-green-plumage": ("squawkabilly",),
    "squawkabilly-white-plumage": ("squawkabillywhite",),
    "squawkabilly-yellow-plumage": ("squawkabillyyellow",),
    "tatsugiri-curly": ("tatsugiri",),
    "tauros-paldea-aqua-breed": ("taurospaldeaaqua",),
    "tauros-paldea-blaze-breed": ("taurospaldeablaze",),
    "tauros-paldea-combat-breed": ("taurospaldeacombat",),
    "terapagos-normal": ("terapagos",),
    "thundurus-incarnate": ("thundurus",),
    "tornadus-incarnate": ("tornadus",),
    "toxtricity-amped": ("toxtricity",),
    "urshifu-single-strike": ("urshifu",),
    "wishiwashi-solo": ("wishiwashi",),
    "wormadam-plant": ("wormadam",),
    "zacian-hero": ("zacian",),
    "zamazenta-hero": ("zamazenta",),
    "zygarde-50": ("zygarde",),
    "zygarde-50-power-construct": ("zygarde",),
    "zygarde-10-power-construct": ("zygarde10",),
    "jellicent-male": ("jellicent",),
    "necrozma-dawn": ("necrozmadawnwings",),
    "necrozma-dusk": ("necrozmaduskmane",),
}


NODE_EXPORT_SCRIPT = r"""
const path = require('path');

const packageDirectory = process.argv[1];
const {Dex} = require(path.join(packageDirectory, 'dist', 'sim', 'dex'));

const sourceDefinitions = [
  {key: 'champions', mod: 'champions', generation: 9},
  {key: 'scarlet-violet', mod: 'gen9', generation: 9},
  {key: 'sword-shield', mod: 'gen8', generation: 8},
  {key: 'bdsp', mod: 'gen8bdsp', generation: 8},
];

function getFallbackLearnset(dex, species) {
  const candidateIds = [
    species.id,
    species.changesFrom ? dex.toID(species.changesFrom) : null,
    species.baseSpecies ? dex.toID(species.baseSpecies) : null,
  ].filter(Boolean);

  const mergedLearnset = {};
  let sourceSpecies = species;
  let foundDirectLearnset = false;

  for (const [position, candidateId] of [
    ...new Set(candidateIds)
  ].entries()) {
    const candidate = dex.species.get(candidateId);
    if (!candidate.exists) continue;

    const learnset = (
      dex.species.getLearnsetData(candidate.id).learnset || {}
    );
    if (!Object.keys(learnset).length) continue;

    if (position === 0) foundDirectLearnset = true;
    if (!foundDirectLearnset) sourceSpecies = candidate;

    for (const [moveId, methods] of Object.entries(learnset)) {
      mergedLearnset[moveId] = [
        ...new Set([...(mergedLearnset[moveId] || []), ...methods]),
      ];
    }
  }

  return {sourceSpecies, learnset: mergedLearnset};
}

function normalizeMoves(dex, moveIds) {
  const movesByNumber = new Map();

  for (const moveId of moveIds) {
    const move = dex.moves.get(moveId);
    if (
      !move.exists ||
      move.isNonstandard ||
      move.num <= 0 ||
      move.num === 1000
    ) continue;

    const existing = movesByNumber.get(move.num);
    if (existing && existing.api_name !== move.id) {
      throw new Error(
        `Move ID ${move.num} is both ${existing.api_name} and ${move.id}`
      );
    }

    movesByNumber.set(move.num, {
      move_id: move.num,
      api_name: move.id,
    });
  }

  return [...movesByNumber.values()].sort(
    (left, right) => left.move_id - right.move_id
  );
}

function getChampionsMoves(dex, species) {
  // Pokémon Showdown resolves the complete valid movepool for the current
  // generation/mod, including inherited/pre-evolution learnsets.
  const movePool = dex.species.getMovePool(species.id);
  return {
    sourceSpecies: species,
    moves: normalizeMoves(dex, movePool),
  };
}

function getFallbackMoves(dex, species, generation) {
  const {sourceSpecies, learnset} = getFallbackLearnset(dex, species);
  const generationPrefix = String(generation);
  const moveIds = [];

  for (const [moveId, learningMethods] of Object.entries(learnset)) {
    if (
      !Array.isArray(learningMethods) ||
      !learningMethods.some(
        method => String(method).startsWith(generationPrefix)
      )
    ) continue;

    moveIds.push(moveId);
  }

  return {
    sourceSpecies,
    moves: normalizeMoves(dex, moveIds),
  };
}

function buildEntry(dex, species, source) {
  const {sourceSpecies, moves} = source.key === 'champions'
    ? getChampionsMoves(dex, species)
    : getFallbackMoves(dex, species, source.generation);

  if (!moves.length) return null;

  const abilities = Object.values(species.abilities || {})
    .map(ability => dex.toID(ability))
    .filter(Boolean)
    .sort();

  return {
    showdown_id: species.id,
    name_en: species.name,
    national_dex: species.num,
    base_species_id: dex.toID(species.baseSpecies),
    form: species.forme || null,
    learnset_source_id: sourceSpecies.id,
    types: (species.types || []).map(type => type.toLowerCase()),
    base_stats: {
      hp: species.baseStats.hp,
      atk: species.baseStats.atk,
      def: species.baseStats.def,
      spa: species.baseStats.spa,
      spd: species.baseStats.spd,
      spe: species.baseStats.spe,
    },
    abilities,
    moves,
  };
}

function exportSource(source) {
  const dex = Dex.mod(source.mod);

  // For Champions export every real species/form known by the mod. Regulation
  // legality is decided later from regulations.json, not from isNonstandard.
  const speciesList = dex.species.all().filter(species => (
    species.exists &&
    species.num > 0 &&
    (
      source.key === 'champions' ||
      !species.isNonstandard
    )
  ));

  const entries = [];
  const seenIds = new Set();

  for (const species of speciesList) {
    if (!species.exists || species.num <= 0) continue;
    if (seenIds.has(species.id)) continue;

    const entry = buildEntry(dex, species, source);
    if (!entry) continue;

    entries.push(entry);
    seenIds.add(species.id);
  }

  entries.sort((left, right) => (
    left.national_dex - right.national_dex ||
    left.showdown_id.localeCompare(right.showdown_id)
  ));

  return {key: source.key, entries};
}

process.stdout.write(JSON.stringify(sourceDefinitions.map(exportSource)));
"""


def normalize_showdown_id(value: str) -> str:
    """Convert a PokéAPI-style name to Showdown's identifier format."""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _append_candidate(candidates: list[str], value: str) -> None:
    """Append one normalized Showdown ID while preserving candidate order."""
    normalized = normalize_showdown_id(value)
    if normalized and normalized not in candidates:
        candidates.append(normalized)


def _family_showdown_id_candidates(api_name: str) -> list[str]:
    """Return robust candidates for retained cosmetic form families."""
    candidates: list[str] = []
    tokens = set(api_name.split("-"))

    if api_name.startswith("squawkabilly-"):
        showdown_by_plumage = {
            "green": "squawkabilly",
            "blue": "squawkabillyblue",
            "yellow": "squawkabillyyellow",
            "white": "squawkabillywhite",
        }
        for plumage, showdown_id in showdown_by_plumage.items():
            if plumage in tokens:
                _append_candidate(candidates, showdown_id)
                _append_candidate(candidates, "squawkabilly")
                break

    if api_name.startswith("tatsugiri-"):
        form_token = next(
            (
                token
                for token in ("curly", "droopy", "stretchy")
                if token in tokens
            ),
            None,
        )
        if form_token is not None:
            if "mega" in tokens:
                _append_candidate(
                    candidates,
                    f"tatsugiri{form_token}mega",
                )
                _append_candidate(candidates, "tatsugiricurlymega")
            else:
                if form_token == "curly":
                    _append_candidate(candidates, "tatsugiri")
                else:
                    _append_candidate(
                        candidates,
                        f"tatsugiri{form_token}",
                    )
                _append_candidate(candidates, "tatsugiri")

    return candidates


def get_showdown_id_candidates(api_name: str) -> list[str]:
    """Return explicit, family-aware, then normalized Showdown IDs."""
    candidates: list[str] = []

    for candidate in SHOWDOWN_ID_ALIASES.get(api_name, ()):
        _append_candidate(candidates, candidate)
    for candidate in _family_showdown_id_candidates(api_name):
        _append_candidate(candidates, candidate)
    _append_candidate(candidates, api_name)

    return candidates


def inherits_base_form_learnset(form: dict[str, Any]) -> bool:
    """Return whether this battle form can inherit a selectable base learnset."""
    api_name = str(form["api_name"])
    return "-mega" in api_name or api_name.endswith("-primal")


def _matching_base_form_for_battle_form(
    form: dict[str, Any],
    forms_by_api_name: dict[str, dict[str, Any]],
    default_forms_by_dex: dict[int, dict[str, Any]],
) -> dict[str, Any] | None:
    """Choose the correct local base appearance for a battle-only form."""
    api_name = str(form["api_name"])
    tokens = set(api_name.split("-"))

    if api_name.startswith("tatsugiri-") and "mega" in tokens:
        form_token = next(
            (
                token
                for token in ("curly", "droopy", "stretchy")
                if token in tokens
            ),
            None,
        )
        if form_token is not None:
            base_form = forms_by_api_name.get(
                f"tatsugiri-{form_token}"
            )
            if base_form is not None:
                return base_form

    return default_forms_by_dex.get(int(form["national_dex"]))


def load_move_index() -> tuple[dict[int, str], str]:
    """Load move IDs and the Showdown version used by moves.json."""
    if not MOVES_FILE.exists():
        raise FileNotFoundError(
            f"Missing {MOVES_FILE}. Run tools/import_moves.py first."
        )

    try:
        moves = json.loads(MOVES_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {MOVES_FILE}: {error}") from error

    if not isinstance(moves, list) or not moves:
        raise ValueError(f"{MOVES_FILE} does not contain a move list.")

    move_index: dict[int, str] = {}
    showdown_versions: set[str] = set()

    for move in moves:
        move_id = move.get("move_id")
        api_name = move.get("api_name")
        source = move.get("source", {})
        version = source.get("version") if isinstance(source, dict) else None

        if not isinstance(move_id, int) or not api_name:
            raise ValueError("moves.json contains an incomplete move record.")
        if move_id in move_index:
            raise ValueError(f"Duplicate move ID in moves.json: {move_id}")

        move_index[move_id] = str(api_name)
        if version:
            showdown_versions.add(str(version))

    if len(showdown_versions) != 1:
        raise ValueError(
            "moves.json must contain exactly one Pokémon Showdown version."
        )

    return move_index, showdown_versions.pop()


def load_current_regulation() -> tuple[str, str, set[int]]:
    """Load the current regulation ID, mod and legal local Pokémon IDs."""
    if not REGULATIONS_FILE.exists():
        raise FileNotFoundError(
            f"Missing {REGULATIONS_FILE}. "
            "Run tools/import_regulations.py first."
        )

    try:
        data = json.loads(REGULATIONS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid JSON in {REGULATIONS_FILE}: {error}"
        ) from error

    if not isinstance(data, dict):
        raise ValueError("regulations.json must contain a JSON object.")

    current_id = data.get("current_regulation_id")
    regulations = data.get("regulations")

    if not isinstance(current_id, str) or not current_id:
        raise ValueError(
            "regulations.json has no valid current_regulation_id."
        )
    if not isinstance(regulations, list):
        raise ValueError(
            "regulations.json has no valid regulations list."
        )

    current = next(
        (
            regulation
            for regulation in regulations
            if isinstance(regulation, dict)
            and regulation.get("id") == current_id
        ),
        None,
    )
    if current is None:
        raise ValueError(
            f"Current regulation {current_id!r} was not found."
        )

    mod = current.get("mod")
    pokemon_ids = current.get("pokemon_ids")

    if not isinstance(mod, str) or not mod:
        raise ValueError(
            f"Current regulation {current_id!r} has no valid mod."
        )
    if (
        not isinstance(pokemon_ids, list)
        or not all(
            isinstance(pokemon_id, int) and pokemon_id > 0
            for pokemon_id in pokemon_ids
        )
    ):
        raise ValueError(
            f"Current regulation {current_id!r} has invalid pokemon_ids."
        )

    # This importer currently exports the live Champions source from the
    # `champions` mod. If a future current regulation uses another mod, fail
    # loudly instead of silently importing the wrong movepools.
    if mod != CHAMPIONS_SOURCE["showdown_mod"]:
        raise RuntimeError(
            f"Current regulation {current_id!r} uses Showdown mod {mod!r}, "
            f"but this importer expects "
            f"{CHAMPIONS_SOURCE['showdown_mod']!r}. Update the importer "
            "before importing the new regulation."
        )

    return current_id, mod, set(pokemon_ids)


def load_pokemon_forms(
    pokemon_file: Path = POKEMON_FILE,
) -> list[dict[str, Any]]:
    """Flatten and validate the nested form records in pokemon_v2.json."""
    if not pokemon_file.exists():
        raise FileNotFoundError(
            f"Missing {pokemon_file}. Run tools/import_pokemon_v4.py first."
        )

    try:
        species_list = json.loads(pokemon_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {pokemon_file}: {error}") from error

    if not isinstance(species_list, list) or not species_list:
        raise ValueError(f"{pokemon_file} does not contain a species list.")

    forms: list[dict[str, Any]] = []
    pokemon_ids: set[int] = set()
    api_names: set[str] = set()

    for species in species_list:
        national_dex = species.get("dex")
        species_forms = species.get("forms")

        if not isinstance(national_dex, int) or national_dex < 1:
            raise ValueError("pokemon_v2.json contains an invalid Dex number.")
        if not isinstance(species_forms, list) or not species_forms:
            raise ValueError(
                f"Dex #{national_dex} has no forms in pokemon_v2.json."
            )

        for form in species_forms:
            pokemon_id = form.get("pokemon_id")
            api_name = form.get("api_name")

            if not isinstance(pokemon_id, int) or pokemon_id < 1:
                raise ValueError(
                    f"Dex #{national_dex} has an invalid Pokémon ID."
                )
            if not isinstance(api_name, str) or not api_name:
                raise ValueError(
                    f"Dex #{national_dex} has a form without an API name."
                )
            if pokemon_id in pokemon_ids:
                raise ValueError(f"Duplicate Pokémon ID: {pokemon_id}")
            if api_name in api_names:
                raise ValueError(f"Duplicate Pokémon API name: {api_name}")

            forms.append(
                {
                    "pokemon_id": pokemon_id,
                    "api_name": api_name,
                    "name_en": form.get("name_en") or api_name,
                    "name_de": (
                        form.get("name_de")
                        or form.get("name_en")
                        or api_name
                    ),
                    "national_dex": national_dex,
                    "is_default": bool(form.get("is_default")),
                    "types": form.get("types", []),
                    "base_stats": form.get("base_stats", {}),
                    "abilities": [
                        ability.get("api_name")
                        for ability in form.get("abilities", [])
                        if (
                            isinstance(ability, dict)
                            and ability.get("api_name")
                        )
                    ],
                }
            )
            pokemon_ids.add(pokemon_id)
            api_names.add(api_name)

    forms.sort(
        key=lambda form: (
            form["national_dex"],
            not form["is_default"],
            form["pokemon_id"],
        )
    )
    return forms


def export_source_learnsets(
    showdown_package: Path,
    node_executable: str,
) -> dict[str, list[dict[str, Any]]]:
    """Run Showdown's Dex loader and return every selected source."""
    try:
        result = subprocess.run(
            [
                node_executable,
                "-e",
                NODE_EXPORT_SCRIPT,
                str(showdown_package),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as error:
        details = error.stderr.strip() or "No Node.js error output."
        raise RuntimeError(
            f"Showdown learnset export failed:\n{details}"
        ) from error

    try:
        exported_sources = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            "Showdown returned invalid learnset JSON."
        ) from error

    if not isinstance(exported_sources, list):
        raise RuntimeError("Showdown did not return a learnset source list.")

    source_entries: dict[str, list[dict[str, Any]]] = {}
    for exported_source in exported_sources:
        if not isinstance(exported_source, dict):
            raise RuntimeError("Showdown returned an invalid learnset source.")
        source_key = exported_source.get("key")
        entries = exported_source.get("entries")

        if source_key not in SOURCE_BY_KEY:
            raise RuntimeError(
                f"Showdown returned an unknown source: {source_key}"
            )
        if not isinstance(entries, list):
            raise RuntimeError(
                f"Showdown returned invalid entries for {source_key}."
            )
        source_entries[str(source_key)] = entries

    if set(source_entries) != set(SOURCE_BY_KEY):
        raise RuntimeError("Showdown did not return all learnset sources.")

    return source_entries


def build_source_indexes(
    entries: list[dict[str, Any]],
) -> tuple[
    dict[str, dict[str, Any]],
    dict[int, list[dict[str, Any]]],
]:
    """Index one Showdown source by ID and National Dex number."""
    by_id: dict[str, dict[str, Any]] = {}
    by_dex: dict[int, list[dict[str, Any]]] = {}

    for entry in entries:
        showdown_id = entry.get("showdown_id")
        national_dex = entry.get("national_dex")

        if not isinstance(showdown_id, str) or not showdown_id:
            raise ValueError("Showdown returned a learnset without an ID.")
        if not isinstance(national_dex, int) or national_dex < 1:
            raise ValueError(
                f"Invalid National Dex number for {showdown_id}."
            )
        if showdown_id in by_id:
            raise ValueError(f"Duplicate Showdown ID: {showdown_id}")

        by_id[showdown_id] = entry
        by_dex.setdefault(national_dex, []).append(entry)

    return by_id, by_dex


def normalize_abilities(abilities: list[str]) -> tuple[str, ...]:
    """Normalize an ability collection for cross-source matching."""
    return tuple(
        sorted(normalize_showdown_id(value) for value in abilities)
    )


def matches_types_and_stats(
    form: dict[str, Any],
    candidate: dict[str, Any],
) -> bool:
    """Return whether stable mechanical fields identify the same form."""
    return (
        form["types"] == candidate.get("types")
        and form["base_stats"] == candidate.get("base_stats")
    )


def find_source_match(
    form: dict[str, Any],
    by_id: dict[str, dict[str, Any]],
    by_dex: dict[int, list[dict[str, Any]]],
    *,
    allow_stats_only_match: bool,
) -> tuple[dict[str, Any] | None, str | None]:
    """Match one PokéAPI form to a Showdown source conservatively."""
    for candidate_id in get_showdown_id_candidates(
        str(form["api_name"])
    ):
        candidate = by_id.get(candidate_id)
        if candidate is not None:
            return candidate, "id"

    dex_candidates = by_dex.get(int(form["national_dex"]), [])
    mechanical_candidates = [
        candidate
        for candidate in dex_candidates
        if matches_types_and_stats(form, candidate)
    ]

    form_abilities = normalize_abilities(list(form["abilities"]))
    exact_candidates = [
        candidate
        for candidate in mechanical_candidates
        if normalize_abilities(
            list(candidate.get("abilities", []))
        ) == form_abilities
    ]

    if exact_candidates:
        move_sets = {
            tuple(
                move["move_id"]
                for move in candidate.get("moves", [])
            )
            for candidate in exact_candidates
        }
        if len(move_sets) == 1:
            return exact_candidates[0], "mechanical"

    if allow_stats_only_match and len(mechanical_candidates) == 1:
        return mechanical_candidates[0], "mechanical"

    return None, None


def validate_move_links(
    entry: dict[str, Any],
    move_index: dict[int, str],
) -> list[int]:
    """Validate temporary Showdown move objects and return sorted IDs."""
    showdown_id = str(entry["showdown_id"])
    moves = entry.get("moves", [])
    move_ids: list[int] = []

    for move in moves:
        move_id = move.get("move_id")
        api_name = move.get("api_name")
        stored_api_name = move_index.get(move_id)

        if stored_api_name is None:
            raise ValueError(
                f"Unknown move ID {move_id} in {showdown_id}'s learnset."
            )
        if stored_api_name != api_name:
            raise ValueError(
                f"Move ID {move_id} is {api_name} in Showdown but "
                f"{stored_api_name} in moves.json."
            )
        move_ids.append(int(move_id))

    if not move_ids:
        raise ValueError(f"Empty selected learnset: {showdown_id}")
    if move_ids != sorted(move_ids):
        raise ValueError(f"Unsorted move IDs for {showdown_id}")
    if len(move_ids) != len(set(move_ids)):
        raise ValueError(f"Duplicate move IDs for {showdown_id}")
    return move_ids


def _find_move_id(
    move_index: dict[int, str],
    api_name: str,
) -> int | None:
    """Return one move ID by Showdown/API name."""
    for move_id, stored_name in move_index.items():
        if stored_name == api_name:
            return move_id
    return None


def validate_champions_sanity(
    learnsets: list[dict[str, Any]],
    move_index: dict[int, str],
) -> None:
    """Catch known Champions-vs-main-series movepool regressions."""
    tera_blast_id = _find_move_id(move_index, "terablast")
    meteor_assault_id = _find_move_id(move_index, "meteorassault")

    champions_entries = [
        entry
        for entry in learnsets
        if entry["available_in_champions"]
    ]

    if tera_blast_id is not None:
        offenders = [
            str(entry["api_name"])
            for entry in champions_entries
            if tera_blast_id in entry["move_ids"]
        ]
        if offenders:
            preview = ", ".join(offenders[:12])
            suffix = (
                ""
                if len(offenders) <= 12
                else f", ... (+{len(offenders) - 12})"
            )
            raise ValueError(
                "Champions movepools unexpectedly contain Tera Blast: "
                f"{preview}{suffix}"
            )

    sirfetchd = next(
        (
            entry
            for entry in champions_entries
            if entry["api_name"] == "sirfetchd"
        ),
        None,
    )
    if sirfetchd is not None:
        if meteor_assault_id is None:
            raise ValueError(
                "moves.json does not contain Meteor Assault."
            )
        if meteor_assault_id not in sirfetchd["move_ids"]:
            raise ValueError(
                "Champions Sirfetch'd learnset is missing Meteor Assault."
            )


def build_learnsets(
    forms: list[dict[str, Any]],
    source_entries: dict[str, list[dict[str, Any]]],
    move_index: dict[int, str],
    showdown_version: str,
    champions_legal_ids: set[int],
) -> tuple[list[dict[str, Any]], Counter[str], int, int]:
    """Select one correct movepool for every Pokédex form."""
    indexes = {
        source_key: build_source_indexes(entries)
        for source_key, entries in source_entries.items()
    }

    default_forms_by_dex = {
        int(form["national_dex"]): form
        for form in forms
        if form["is_default"]
    }
    forms_by_api_name = {
        str(form["api_name"]): form
        for form in forms
    }

    learnsets: list[dict[str, Any]] = []
    source_counts: Counter[str] = Counter()
    inherited_count = 0
    mechanical_match_count = 0

    for form in forms:
        pokemon_id = int(form["pokemon_id"])
        available_in_champions = pokemon_id in champions_legal_ids

        selected_source: dict[str, Any] | None = None
        selected_entry: dict[str, Any] | None = None
        match_method: str | None = None

        # Critical rule:
        # - legal in current Champions regulation -> Champions ONLY
        # - not legal -> main-series fallbacks ONLY
        candidate_sources = (
            (CHAMPIONS_SOURCE,)
            if available_in_champions
            else FALLBACK_LEARNSET_SOURCES
        )

        for source in candidate_sources:
            source_key = str(source["key"])
            by_id, by_dex = indexes[source_key]

            selected_entry, match_method = find_source_match(
                form,
                by_id,
                by_dex,
                allow_stats_only_match=source_key != "champions",
            )

            if (
                selected_entry is None
                and inherits_base_form_learnset(form)
            ):
                base_form = _matching_base_form_for_battle_form(
                    form,
                    forms_by_api_name,
                    default_forms_by_dex,
                )
                if base_form is not None:
                    base_entry, _ = find_source_match(
                        base_form,
                        by_id,
                        by_dex,
                        allow_stats_only_match=(
                            source_key != "champions"
                        ),
                    )
                    if base_entry is not None:
                        selected_entry = {
                            **base_entry,
                            "showdown_id": normalize_showdown_id(
                                str(form["api_name"])
                            ),
                            "learnset_source_id": (
                                base_entry["showdown_id"]
                            ),
                        }
                        match_method = "base-form"

            if selected_entry is not None:
                selected_source = source
                break

        base_record: dict[str, Any] = {
            "pokemon_id": form["pokemon_id"],
            "api_name": form["api_name"],
            "name_en": form["name_en"],
            "name_de": form["name_de"],
            "national_dex": form["national_dex"],
            "is_default": form["is_default"],
        }

        if available_in_champions and (
            selected_source is None or selected_entry is None
        ):
            raise ValueError(
                f"{form['api_name']} (pokemon_id={pokemon_id}) is legal "
                "in the current Champions regulation but no Champions "
                "learnset could be matched. No fallback was used."
            )

        if selected_source is None or selected_entry is None:
            base_record.update(
                {
                    "showdown_id": normalize_showdown_id(
                        str(form["api_name"])
                    ),
                    "learnset_source_id": None,
                    "available_in_champions": False,
                    "learnset_source": None,
                    "source_generation": None,
                    "is_fallback": False,
                    "move_ids": [],
                    "note": NO_CURRENT_LEARNSET_NOTE,
                    "source": None,
                }
            )
            source_counts["none"] += 1
        else:
            move_ids = validate_move_links(
                selected_entry,
                move_index,
            )
            source_key = str(selected_source["key"])

            base_record.update(
                {
                    "showdown_id": selected_entry["showdown_id"],
                    "learnset_source_id": (
                        selected_entry["learnset_source_id"]
                    ),
                    "available_in_champions": (
                        available_in_champions
                    ),
                    "learnset_source": source_key,
                    "source_generation": (
                        selected_source["generation"]
                    ),
                    "is_fallback": (
                        selected_source["is_fallback"]
                    ),
                    "move_ids": move_ids,
                    "note": None,
                    "source": {
                        "database": "pokemon-showdown",
                        "version": showdown_version,
                        "mod": selected_source["showdown_mod"],
                    },
                }
            )
            source_counts[source_key] += 1
            inherited_count += (
                selected_entry["showdown_id"]
                != selected_entry["learnset_source_id"]
            )
            mechanical_match_count += (
                match_method == "mechanical"
            )

        learnsets.append(base_record)

    validate_complete_learnsets(
        learnsets,
        forms,
        champions_legal_ids,
    )
    validate_champions_sanity(learnsets, move_index)

    return (
        learnsets,
        source_counts,
        inherited_count,
        mechanical_match_count,
    )


def validate_complete_learnsets(
    learnsets: list[dict[str, Any]],
    forms: list[dict[str, Any]],
    champions_legal_ids: set[int],
) -> None:
    """Verify one-to-one form coverage and source invariants."""
    if len(learnsets) != len(forms):
        raise ValueError(
            "Not every pokemon_v2.json form has one learnset."
        )

    expected_ids = {form["pokemon_id"] for form in forms}
    actual_ids = [entry["pokemon_id"] for entry in learnsets]

    if len(actual_ids) != len(set(actual_ids)):
        raise ValueError(
            "learnsets.json contains duplicate Pokémon IDs."
        )
    if set(actual_ids) != expected_ids:
        raise ValueError(
            "learnsets.json does not match pokemon_v2.json."
        )

    for entry in learnsets:
        pokemon_id = int(entry["pokemon_id"])
        source_key = entry["learnset_source"]
        move_ids = entry["move_ids"]
        expected_champions = pokemon_id in champions_legal_ids

        if (
            bool(entry["available_in_champions"])
            != expected_champions
        ):
            raise ValueError(
                f"Wrong Champions availability for "
                f"{entry['api_name']}."
            )

        if source_key is None:
            if expected_champions:
                raise ValueError(
                    f"Champions-legal Pokémon has no learnset: "
                    f"{entry['api_name']}"
                )
            if move_ids or entry["source"] is not None:
                raise ValueError(
                    f"Source-less entry contains data: "
                    f"{entry['api_name']}"
                )
            if entry["note"] != NO_CURRENT_LEARNSET_NOTE:
                raise ValueError(
                    f"Missing no-learnset note: "
                    f"{entry['api_name']}"
                )
            continue

        source = SOURCE_BY_KEY.get(source_key)
        if source is None:
            raise ValueError(
                f"Unknown learnset source for "
                f"{entry['api_name']}: {source_key}"
            )
        if not move_ids or entry["source"] is None:
            raise ValueError(
                f"Incomplete learnset entry: "
                f"{entry['api_name']}"
            )
        if entry["source"]["mod"] != source["showdown_mod"]:
            raise ValueError(
                f"Wrong source mod for {entry['api_name']}."
            )

        if expected_champions:
            if source_key != "champions":
                raise ValueError(
                    f"Champions-legal Pokémon fell back to "
                    f"{source_key}: {entry['api_name']}"
                )
        elif source_key == "champions":
            raise ValueError(
                f"Non-current Pokémon incorrectly uses Champions "
                f"learnset: {entry['api_name']}"
            )

        if entry["is_fallback"] != source["is_fallback"]:
            raise ValueError(
                f"Wrong fallback flag for {entry['api_name']}."
            )


def import_learnsets(
    limit: int | None = None,
    pokemon_file: Path = POKEMON_FILE,
) -> tuple[
    Path,
    int,
    int,
    Counter[str],
    int,
    int,
    int,
    str,
    str,
]:
    """Export, select, validate and write every form's movepool."""
    if limit is not None and limit < 1:
        raise ValueError("--limit must be at least 1.")

    move_index, moves_version = load_move_index()
    current_regulation_id, _, champions_legal_ids = (
        load_current_regulation()
    )
    forms = load_pokemon_forms(pokemon_file)

    if limit is not None:
        forms = forms[:limit]

    # Limit legality to forms participating in this import. This keeps preview
    # validation correct without changing the real regulation data.
    imported_form_ids = {
        int(form["pokemon_id"])
        for form in forms
    }
    champions_legal_ids = (
        champions_legal_ids & imported_form_ids
    )

    node_executable = require_node()
    showdown_commit = load_showdown_commit()
    tarball, npm_version = download_showdown_package()
    showdown_version = showdown_snapshot_version(
        npm_version,
        showdown_commit,
    )

    if showdown_version != moves_version:
        raise RuntimeError(
            "Pokémon Showdown was updated after moves.json was created "
            f"({moves_version} -> {showdown_version}). Run "
            "tools/import_moves.py again, then retry the learnset import."
        )

    with tempfile.TemporaryDirectory(
        prefix="cordys-showdown-"
    ) as temporary_directory:
        showdown_package = extract_showdown_dist(
            tarball,
            Path(temporary_directory),
        )
        overlay_live_showdown_mods(
            showdown_package,
            showdown_commit,
            {"champions"},
            required_mods={"champions"},
        )
        source_entries = export_source_learnsets(
            showdown_package,
            node_executable,
        )

    (
        learnsets,
        source_counts,
        inherited_count,
        mechanical_match_count,
    ) = build_learnsets(
        forms,
        source_entries,
        move_index,
        showdown_version,
        champions_legal_ids,
    )

    output_file = (
        PREVIEW_OUTPUT_FILE
        if limit is not None
        else OUTPUT_FILE
    )
    write_json_atomically(learnsets, output_file)

    link_count = sum(
        len(entry["move_ids"])
        for entry in learnsets
    )
    champions_available_count = sum(
        bool(entry["available_in_champions"])
        for entry in learnsets
    )

    return (
        output_file,
        len(learnsets),
        link_count,
        source_counts,
        champions_available_count,
        inherited_count,
        mechanical_match_count,
        showdown_version,
        current_regulation_id,
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Import current Champions movepools for legal Pokémon and "
            "Scarlet/Violet, Sword/Shield or BDSP fallbacks for the "
            "remaining Pokédex forms."
        )
    )
    parser.add_argument(
        "--limit",
        type=int,
        help=(
            "Import only the first N forms and write "
            "learnsets_preview.json."
        ),
    )
    return parser.parse_args()


def main() -> None:
    print(
        "Cordy's Lab learnset importer v4 "
        "(import_learnset.py)"
    )
    arguments = parse_arguments()

    (
        output_file,
        learnset_count,
        link_count,
        source_counts,
        champions_available_count,
        inherited_count,
        mechanical_match_count,
        showdown_version,
        current_regulation_id,
    ) = import_learnsets(limit=arguments.limit)

    print()
    print(
        f"Done! Imported {learnset_count} form learnsets from "
        f"Pokémon Showdown {showdown_version}."
    )
    print(
        f"Current Champions regulation: "
        f"{current_regulation_id}"
    )

    for source in LEARNSET_SOURCES:
        suffix = (
            " fallbacks"
            if source["is_fallback"]
            else " learnset source"
        )
        print(
            f"{source['label']}{suffix}: "
            f"{source_counts[source['key']]}"
        )

    print(
        f"Available in Pokémon Champions: "
        f"{champions_available_count}"
    )
    print(
        f"No current learnset: "
        f"{source_counts['none']}"
    )
    print(
        f"Pokémon-to-move links: {link_count}"
    )
    print(
        f"Inherited form learnsets: {inherited_count}"
    )
    print(
        f"Mechanical ID matches: "
        f"{mechanical_match_count}"
    )
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    main()
