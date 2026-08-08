"""Cordy's Lab learnset importer — version 2.

Build the learnset database used by the Cordy's Lab Pokédex.

Every mechanically distinct form from ``data/pokemon_v2.json`` receives
exactly one record. Learnsets are selected independently from the move values
stored in ``data/moves.json`` and use this priority:

1. Pokémon Champions
2. Scarlet/Violet
3. Sword/Shield
4. Brilliant Diamond/Shining Pearl

Legends games and generations before Generation 8 are deliberately excluded.
If none of the selected games contains the form, the importer stores an empty
movepool and the note ``No set is currently available.``

Pokémon Showdown stores historical learning methods together. The importer
therefore keeps only methods from the selected source generation instead of
accidentally adding older transfer-only moves. Showdown's own Dex loader is
used for mod inheritance and form learnset inheritance.

Version 2 adds robust family-aware matching for the cosmetic Squawkabilly and
Tatsugiri forms retained by the Pokémon importer, including all Tatsugiri Mega
forms regardless of the token order used by the upstream API name.

Run from the project root with:

    python3 tools/import_learnsets_v2.py

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
        require_node,
        write_json_atomically,
    )
except ModuleNotFoundError:
    # Supports ``python -m tools.import_learnsets_v2`` as well as executing the
    # file directly with ``python tools/import_learnsets_v2.py``.
    from tools.import_moves import (
        download_showdown_package,
        extract_showdown_dist,
        require_node,
        write_json_atomically,
    )


PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
DATA_DIRECTORY = PROJECT_DIRECTORY / "data"
POKEMON_FILE = DATA_DIRECTORY / "pokemon_v2.json"
MOVES_FILE = DATA_DIRECTORY / "moves.json"
OUTPUT_FILE = DATA_DIRECTORY / "learnsets.json"
PREVIEW_OUTPUT_FILE = DATA_DIRECTORY / "learnsets_preview.json"

NO_CURRENT_LEARNSET_NOTE = "No set is currently available."

# First match wins. This is the learnset priority; the displayed values for
# every move remain governed independently by MOVE_VALUE_SOURCES in
# import_moves.py.
LEARNSET_SOURCES = (
    {
        "key": "champions",
        "showdown_mod": "champions",
        "label": "Pokémon Champions",
        "generation": 9,
        "is_fallback": False,
    },
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

function getLearnset(dex, species, mergeInherited) {
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

    if (!mergeInherited) break;
  }

  return {sourceSpecies, learnset: mergedLearnset};
}

function getLegalMoves(dex, species, generation, mergeInherited) {
  const {sourceSpecies, learnset} = getLearnset(
    dex,
    species,
    mergeInherited
  );
  const movesByNumber = new Map();
  const generationPrefix = String(generation);

  for (const [moveId, learningMethods] of Object.entries(learnset)) {
    if (
      !Array.isArray(learningMethods) ||
      !learningMethods.some(method => String(method).startsWith(generationPrefix))
    ) continue;

    const move = dex.moves.get(moveId);
    if (
      !move.exists || move.isNonstandard || move.num <= 0 || move.num === 1000
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

  const moves = [...movesByNumber.values()].sort(
    (left, right) => left.move_id - right.move_id
  );
  return {sourceSpecies, moves};
}

function buildEntry(dex, species, source) {
  const {sourceSpecies, moves} = getLegalMoves(
    dex,
    species,
    source.generation,
    source.key !== 'champions'
  );
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
  const speciesList = dex.species.all().filter(species => (
    species.exists && !species.isNonstandard && species.num > 0
  ));

  const entries = [];
  const seenIds = new Set();

  for (const species of speciesList) {
    if (!species.exists || species.isNonstandard || species.num <= 0) {
      if (source.key === 'champions') {
        throw new Error(`Invalid Champions species: ${species.id}`);
      }
      continue;
    }
    if (seenIds.has(species.id)) continue;

    const entry = buildEntry(dex, species, source);
    if (!entry) {
      if (source.key === 'champions') {
        throw new Error(`No Champions learnset found for ${species.name}`);
      }
      continue;
    }

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
    """Return robust candidates for retained cosmetic form families.

    The Pokémon importer deliberately retains all Squawkabilly plumages and
    all Tatsugiri base/Mega forms. Upstream API names can change token order,
    while Showdown uses compact canonical IDs, so these families need a small
    amount of semantic candidate generation instead of pure punctuation
    stripping.
    """
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
                # If a source collapses cosmetic plumages, they share the
                # selectable base species' learnset.
                _append_candidate(candidates, "squawkabilly")
                break

    if api_name.startswith("tatsugiri-"):
        form_token = next(
            (token for token in ("curly", "droopy", "stretchy") if token in tokens),
            None,
        )
        if form_token is not None:
            if "mega" in tokens:
                _append_candidate(candidates, f"tatsugiri{form_token}mega")
                # Showdown's generic Mega alias resolves to Curly-Mega. The
                # three retained Mega appearances share the same learnset; use
                # it only as a final family fallback if a cosmetic ID is absent.
                _append_candidate(candidates, "tatsugiricurlymega")
            else:
                if form_token == "curly":
                    _append_candidate(candidates, "tatsugiri")
                else:
                    _append_candidate(candidates, f"tatsugiri{form_token}")
                # Older/fallback sources may collapse all three appearances.
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

    # Keep each retained Tatsugiri Mega tied to the corresponding base
    # appearance rather than always falling back to Curly/default.
    if api_name.startswith("tatsugiri-") and "mega" in tokens:
        form_token = next(
            (token for token in ("curly", "droopy", "stretchy") if token in tokens),
            None,
        )
        if form_token is not None:
            base_form = forms_by_api_name.get(f"tatsugiri-{form_token}")
            if base_form is not None:
                return base_form

    return default_forms_by_dex.get(int(form["national_dex"]))


def load_move_index() -> tuple[dict[int, str], str]:
    """Load move IDs and the Showdown version used by ``moves.json``."""
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
                    "name_de": form.get("name_de") or form.get("name_en") or api_name,
                    "national_dex": national_dex,
                    "is_default": bool(form.get("is_default")),
                    "types": form.get("types", []),
                    "base_stats": form.get("base_stats", {}),
                    "abilities": [
                        ability.get("api_name")
                        for ability in form.get("abilities", [])
                        if isinstance(ability, dict) and ability.get("api_name")
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
) -> tuple[dict[str, dict[str, Any]], dict[int, list[dict[str, Any]]]]:
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
    return tuple(sorted(normalize_showdown_id(value) for value in abilities))


def matches_types_and_stats(
    form: dict[str, Any],
    candidate: dict[str, Any],
) -> bool:
    """Return whether the stable mechanical fields identify the same form."""
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
    for candidate_id in get_showdown_id_candidates(str(form["api_name"])):
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
        if normalize_abilities(list(candidate.get("abilities", [])))
        == form_abilities
    ]

    if exact_candidates:
        move_sets = {
            tuple(move["move_id"] for move in candidate.get("moves", []))
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


def build_learnsets(
    forms: list[dict[str, Any]],
    source_entries: dict[str, list[dict[str, Any]]],
    move_index: dict[int, str],
    showdown_version: str,
) -> tuple[list[dict[str, Any]], Counter[str], int, int]:
    """Select the highest-priority movepool for every Pokédex form."""
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
        selected_source: dict[str, Any] | None = None
        selected_entry: dict[str, Any] | None = None
        match_method: str | None = None

        champions_by_id, champions_by_dex = indexes["champions"]
        champions_entry, _ = find_source_match(
            form,
            champions_by_id,
            champions_by_dex,
            allow_stats_only_match=False,
        )
        available_in_champions = champions_entry is not None

        for source in LEARNSET_SOURCES:
            by_id, by_dex = indexes[str(source["key"])]
            selected_entry, match_method = find_source_match(
                form,
                by_id,
                by_dex,
                allow_stats_only_match=source["key"] != "champions",
            )

            if selected_entry is None and inherits_base_form_learnset(form):
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
                        allow_stats_only_match=(source["key"] != "champions"),
                    )
                    if base_entry is not None:
                        selected_entry = {
                            **base_entry,
                            "showdown_id": normalize_showdown_id(
                                str(form["api_name"])
                            ),
                            "learnset_source_id": base_entry["showdown_id"],
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

        if selected_source is None or selected_entry is None:
            base_record.update(
                {
                    "showdown_id": normalize_showdown_id(str(form["api_name"])),
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
            move_ids = validate_move_links(selected_entry, move_index)
            source_key = str(selected_source["key"])

            base_record.update(
                {
                    "showdown_id": selected_entry["showdown_id"],
                    "learnset_source_id": selected_entry["learnset_source_id"],
                    "available_in_champions": available_in_champions,
                    "learnset_source": source_key,
                    "source_generation": selected_source["generation"],
                    "is_fallback": selected_source["is_fallback"],
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
            mechanical_match_count += match_method == "mechanical"

        learnsets.append(base_record)

    validate_complete_learnsets(learnsets, forms)
    return (
        learnsets,
        source_counts,
        inherited_count,
        mechanical_match_count,
    )


def validate_complete_learnsets(
    learnsets: list[dict[str, Any]],
    forms: list[dict[str, Any]],
) -> None:
    """Verify complete one-to-one form coverage and source invariants."""
    if len(learnsets) != len(forms):
        raise ValueError("Not every pokemon_v2.json form has one learnset.")

    expected_ids = {form["pokemon_id"] for form in forms}
    actual_ids = [entry["pokemon_id"] for entry in learnsets]

    if len(actual_ids) != len(set(actual_ids)):
        raise ValueError("learnsets.json contains duplicate Pokémon IDs.")
    if set(actual_ids) != expected_ids:
        raise ValueError("learnsets.json does not match pokemon_v2.json.")

    for entry in learnsets:
        source_key = entry["learnset_source"]
        move_ids = entry["move_ids"]

        if source_key is None:
            if move_ids or entry["source"] is not None:
                raise ValueError(
                    f"Source-less entry contains data: {entry['api_name']}"
                )
            if entry["note"] != NO_CURRENT_LEARNSET_NOTE:
                raise ValueError(
                    f"Missing no-learnset note: {entry['api_name']}"
                )
            continue

        source = SOURCE_BY_KEY.get(source_key)
        if source is None:
            raise ValueError(
                f"Unknown learnset source for {entry['api_name']}: "
                f"{source_key}"
            )
        if not move_ids or entry["source"] is None:
            raise ValueError(
                f"Incomplete learnset entry: {entry['api_name']}"
            )
        if entry["source"]["mod"] != source["showdown_mod"]:
            raise ValueError(
                f"Wrong source mod for {entry['api_name']}."
            )
        if entry["available_in_champions"] and source_key != "champions":
            raise ValueError(
                f"Wrong Champions availability for {entry['api_name']}."
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
]:
    """Export, select, validate and write every form's movepool."""
    if limit is not None and limit < 1:
        raise ValueError("--limit must be at least 1.")

    move_index, moves_version = load_move_index()
    forms = load_pokemon_forms(pokemon_file)
    if limit is not None:
        forms = forms[:limit]

    node_executable = require_node()
    tarball, showdown_version = download_showdown_package()

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
    )

    output_file = PREVIEW_OUTPUT_FILE if limit is not None else OUTPUT_FILE
    write_json_atomically(learnsets, output_file)

    link_count = sum(len(entry["move_ids"]) for entry in learnsets)
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
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Import prioritized Champions, Scarlet/Violet, Sword/Shield "
            "and BDSP movepools for every pokemon_v2.json form."
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
    print("Cordy's Lab learnset importer v2")
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
    ) = import_learnsets(limit=arguments.limit)

    print()
    print(
        f"Done! Imported {learnset_count} form learnsets from "
        f"Pokémon Showdown {showdown_version}."
    )
    for source in LEARNSET_SOURCES:
        suffix = " fallbacks" if source["is_fallback"] else " learnset source"
        print(
            f"{source['label']}{suffix}: "
            f"{source_counts[source['key']]}"
        )
    print(f"Available in Pokémon Champions: {champions_available_count}")
    print(f"No current learnset: {source_counts['none']}")
    print(f"Pokémon-to-move links: {link_count}")
    print(f"Inherited form learnsets: {inherited_count}")
    print(f"Mechanical ID matches: {mechanical_match_count}")
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    main()