"""apps/desktop/tools/pokedex/data.py — Pokédex data layer version 74.

Load, validate, index, and search the shared Cordy's Lab Pokédex data.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any


REGIONAL_TOKENS = ("alola", "galar", "hisui", "paldea")

# PokéAPI stores the parent species, but not always the exact parent form.
# These evolutions need an explicit form mapping.
PARENT_FORM_OVERRIDES = {
    "perrserker": "meowth-galar",
    "sirfetchd": "farfetchd-galar",
    "cursola": "corsola-galar",
    "obstagoon": "linoone-galar",
    "runerigus": "yamask-galar",
    "mr-rime": "mr-mime-galar",
    "sneasler": "sneasel-hisui",
    "overqwil": "qwilfish-hisui",
    "basculegion-male": "basculin-white-striped",
    "basculegion-female": "basculin-white-striped",
    "basculegion": "basculin-white-striped",
    "clodsire": "wooper-paldea",
}


STAT_NAMES = {
    "de": {
        "hp": "KP",
        "atk": "Angriff",
        "def": "Verteidigung",
        "spa": "Sp.-Angriff",
        "spd": "Sp.-Verteidigung",
        "spe": "Initiative",
    },
    "en": {
        "hp": "HP",
        "atk": "Attack",
        "def": "Defense",
        "spa": "Sp. Attack",
        "spd": "Sp. Defense",
        "spe": "Speed",
    },
}



def normalize(value: str) -> str:
    """Normalize names so German, English, and API names are searchable."""
    value = unicodedata.normalize("NFKC", value).casefold().strip()
    value = value.replace("♀", " female").replace("♂", " male")
    value = value.replace("_", " ").replace("-", " ")
    value = re.sub(r"[^\w\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def load_json_list(file_path: Path) -> list[dict[str, Any]]:
    if not file_path.is_file():
        raise FileNotFoundError(f"Missing data file: {file_path}")

    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {file_path}: {error}") from error

    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON list in {file_path}")
    return data


def load_json_object(file_path: Path) -> dict[str, Any]:
    if not file_path.is_file():
        raise FileNotFoundError(f"Missing data file: {file_path}")

    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {file_path}: {error}") from error

    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object in {file_path}")
    return data


class PokedexData:
    """Load, index, and cross-check the shared Pokédex data files."""

    def __init__(self, data_directory: Path) -> None:
        self.pokemon = load_json_list(data_directory / "pokemon_v2.json")
        self.moves = load_json_list(data_directory / "moves.json")
        self.learnsets = load_json_list(data_directory / "learnsets.json")
        self.regulations_data = load_json_object(
            data_directory / "regulations.json"
        )

        self.forms: list[dict[str, Any]] = []
        for species in self.pokemon:
            dex = species.get("dex")
            forms = species.get("forms")
            if not isinstance(dex, int) or not isinstance(forms, list):
                raise ValueError("pokemon_v2.json contains an invalid species.")
            evolves_from_species_id = species.get("evolves_from_species_id")
            if evolves_from_species_id is not None and not isinstance(
                evolves_from_species_id, int
            ):
                raise ValueError(
                    "pokemon_v2.json contains an invalid evolves_from_species_id."
                )
            for form in forms:
                self.forms.append(
                    {
                        **form,
                        "national_dex": dex,
                        "evolves_from_species_id": evolves_from_species_id,
                    }
                )

        self.moves_by_id = self._unique_index(
            self.moves,
            "move_id",
            "moves.json",
        )
        self.learnsets_by_pokemon_id = self._unique_index(
            self.learnsets,
            "pokemon_id",
            "learnsets.json",
        )
        self.forms_by_pokemon_id = self._unique_index(
            self.forms,
            "pokemon_id",
            "pokemon_v2.json",
        )
        self.forms_by_api_name = {
            str(form["api_name"]): form
            for form in self.forms
            if form.get("api_name")
        }
        self.forms_by_species_id: dict[int, list[dict[str, Any]]] = defaultdict(list)
        self.default_form_by_species_id: dict[int, dict[str, Any]] = {}
        for form in self.forms:
            species_id = int(form["national_dex"])
            self.forms_by_species_id[species_id].append(form)
            if bool(form.get("is_default")):
                self.default_form_by_species_id[species_id] = form

        for species_id, forms in self.forms_by_species_id.items():
            if species_id not in self.default_form_by_species_id:
                self.default_form_by_species_id[species_id] = min(
                    forms,
                    key=lambda item: int(item["pokemon_id"]),
                )

        self._resolved_move_ids_cache: dict[int, set[int]] = {}
        self.link_count = self._validate_links()
        self._load_regulations()

    def _load_regulations(self) -> None:
        """Validate regulations.json and prepare fast form lookups."""
        records = self.regulations_data.get("regulations")
        current_id = self.regulations_data.get("current_regulation_id")

        if not isinstance(records, list) or not records:
            raise ValueError(
                "regulations.json must contain a non-empty regulations list."
            )
        if not isinstance(current_id, str) or not current_id:
            raise ValueError(
                "regulations.json contains an invalid current_regulation_id."
            )

        self.regulations: list[dict[str, Any]] = []
        self.regulations_by_id: dict[str, dict[str, Any]] = {}
        self.regulation_pokemon_ids: dict[str, set[int]] = {}
        known_form_ids = set(self.forms_by_pokemon_id)

        for record in records:
            if not isinstance(record, dict):
                raise ValueError(
                    "regulations.json contains an invalid record."
                )

            regulation_id = record.get("id")
            name = record.get("name")
            pokemon_ids = record.get("pokemon_ids")

            if not isinstance(regulation_id, str) or not regulation_id:
                raise ValueError(
                    "regulations.json contains an invalid regulation id."
                )
            if regulation_id in self.regulations_by_id:
                raise ValueError(
                    f"Duplicate regulation id {regulation_id!r} "
                    "in regulations.json."
                )
            if not isinstance(name, str) or not name:
                raise ValueError(
                    f"Regulation {regulation_id!r} has an invalid name."
                )
            if not isinstance(pokemon_ids, list) or not all(
                isinstance(pokemon_id, int)
                for pokemon_id in pokemon_ids
            ):
                raise ValueError(
                    f"Regulation {regulation_id!r} has invalid pokemon_ids."
                )

            allowed_ids = set(pokemon_ids)
            unknown_ids = allowed_ids - known_form_ids
            if unknown_ids:
                raise ValueError(
                    f"Regulation {regulation_id!r} references unknown "
                    f"Pokémon IDs: {sorted(unknown_ids)[:10]}"
                )

            stored = dict(record)
            self.regulations.append(stored)
            self.regulations_by_id[regulation_id] = stored
            self.regulation_pokemon_ids[regulation_id] = allowed_ids

        if current_id not in self.regulations_by_id:
            raise ValueError(
                "current_regulation_id is not present in regulations.json."
            )

        self.current_regulation_id = current_id

    def regulation_choices(self) -> list[dict[str, Any]]:
        """Return current regulation, National Dex, then expired regulations."""
        current = self.regulations_by_id[self.current_regulation_id]

        choices: list[dict[str, Any]] = [dict(current)]
        choices.append(
            {
                "id": "national_dex",
                "name": "National Dex",
                "status": "all",
            }
        )
        choices.extend(
            dict(record)
            for record in self.regulations
            if str(record.get("id")) != self.current_regulation_id
        )
        return choices

    def forms_for_regulation(
        self,
        regulation_id: str,
    ) -> list[dict[str, Any]]:
        """Return all forms belonging to one search regulation scope."""
        if regulation_id == "national_dex":
            return list(self.forms)

        allowed_ids = self.regulation_pokemon_ids.get(regulation_id)
        if allowed_ids is None:
            raise ValueError(f"Unknown regulation id: {regulation_id}")

        return [
            form
            for form in self.forms
            if int(form["pokemon_id"]) in allowed_ids
        ]

    def form_in_regulation(
        self,
        form: dict[str, Any],
        regulation_id: str,
    ) -> bool:
        """Return whether a form belongs to the selected regulation scope."""
        if regulation_id == "national_dex":
            return True

        allowed_ids = self.regulation_pokemon_ids.get(regulation_id)
        if allowed_ids is None:
            return False

        pokemon_id = form.get("pokemon_id")
        return (
            isinstance(pokemon_id, int)
            and pokemon_id in allowed_ids
        )

    @staticmethod
    def _unique_index(
        records: list[dict[str, Any]],
        key: str,
        file_name: str,
    ) -> dict[int, dict[str, Any]]:
        index: dict[int, dict[str, Any]] = {}
        for record in records:
            record_id = record.get(key)
            if not isinstance(record_id, int):
                raise ValueError(f"Invalid {key} in {file_name}.")
            if record_id in index:
                raise ValueError(f"Duplicate {key} {record_id} in {file_name}.")
            index[record_id] = record
        return index

    def _validate_links(self) -> int:
        form_ids = set(self.forms_by_pokemon_id)
        learnset_ids = set(self.learnsets_by_pokemon_id)
        if form_ids != learnset_ids:
            missing = sorted(form_ids - learnset_ids)
            extra = sorted(learnset_ids - form_ids)
            raise ValueError(
                "pokemon_v2.json and learnsets.json do not cover the same "
                f"forms (missing={missing[:5]}, extra={extra[:5]})."
            )

        link_count = 0
        for learnset in self.learnsets:
            move_ids = learnset.get("move_ids")
            if not isinstance(move_ids, list):
                raise ValueError(
                    f"Invalid move_ids for {learnset.get('api_name', '?')}."
                )
            unknown = [
                move_id
                for move_id in move_ids
                if move_id not in self.moves_by_id
            ]
            if unknown:
                raise ValueError(
                    f"Unknown move IDs for {learnset.get('api_name', '?')}: "
                    f"{unknown[:5]}"
                )
            link_count += len(move_ids)
        return link_count

    def search(self, query: str) -> list[dict[str, Any]]:
        query = query.strip()
        if query.isdigit():
            dex = int(query)
            return [
                form
                for form in self.forms
                if form["national_dex"] == dex
            ]

        normalized_query = normalize(query)
        if not normalized_query:
            return []

        ranked: list[tuple[int, int, int, dict[str, Any]]] = []
        for form in self.forms:
            names = {
                normalize(str(form.get("api_name", ""))),
                normalize(str(form.get("name_de", ""))),
                normalize(str(form.get("name_en", ""))),
            }
            if normalized_query in names:
                rank = 0
            elif any(name.startswith(normalized_query) for name in names):
                rank = 1
            elif any(normalized_query in name for name in names):
                rank = 2
            else:
                continue
            ranked.append(
                (
                    rank,
                    int(form["national_dex"]),
                    int(form["pokemon_id"]),
                    form,
                )
            )

        ranked.sort(key=lambda item: item[:3])
        exact_matches = [item[3] for item in ranked if item[0] == 0]
        return exact_matches or [item[3] for item in ranked[:20]]

    @staticmethod
    def _regional_token(api_name: str) -> str | None:
        parts = set(api_name.split("-"))
        return next((token for token in REGIONAL_TOKENS if token in parts), None)

    def _select_parent_form(
        self,
        form: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Choose the stored form that represents this form's pre-evolution."""
        api_name = str(form.get("api_name", ""))
        override_name = PARENT_FORM_OVERRIDES.get(api_name)
        if override_name:
            override = self.forms_by_api_name.get(override_name)
            if override is not None:
                return override

        parent_species_id = form.get("evolves_from_species_id")
        if parent_species_id is None:
            return None

        candidates = self.forms_by_species_id.get(int(parent_species_id), [])
        if not candidates:
            return None

        regional_token = self._regional_token(api_name)
        if regional_token:
            regional_candidates = [
                candidate
                for candidate in candidates
                if regional_token
                in str(candidate.get("api_name", "")).split("-")
            ]
            if regional_candidates:
                return min(
                    regional_candidates,
                    key=lambda item: (
                        not bool(item.get("is_default")),
                        int(item["pokemon_id"]),
                    ),
                )

        return self.default_form_by_species_id.get(int(parent_species_id))

    def _collect_resolved_move_ids(
        self,
        pokemon_id: int,
        *,
        visiting: set[int],
    ) -> set[int]:
        """Collect direct and inherited move IDs recursively."""
        cached = self._resolved_move_ids_cache.get(pokemon_id)
        if cached is not None:
            return set(cached)

        if pokemon_id in visiting:
            return set()

        learnset = self.learnsets_by_pokemon_id[pokemon_id]
        move_ids = {int(move_id) for move_id in learnset["move_ids"]}

        form = self.forms_by_pokemon_id[pokemon_id]
        parent_form = self._select_parent_form(form)
        if parent_form is not None:
            visiting.add(pokemon_id)
            try:
                move_ids.update(
                    self._collect_resolved_move_ids(
                        int(parent_form["pokemon_id"]),
                        visiting=visiting,
                    )
                )
            finally:
                visiting.remove(pokemon_id)

        self._resolved_move_ids_cache[pokemon_id] = set(move_ids)
        return move_ids

    def resolved_moves(self, pokemon_id: int) -> list[dict[str, Any]]:
        """Return this form's moves plus all moves from its pre-evolutions."""
        move_ids = self._collect_resolved_move_ids(
            int(pokemon_id),
            visiting=set(),
        )
        return [
            self.moves_by_id[move_id]
            for move_id in sorted(move_ids)
        ]