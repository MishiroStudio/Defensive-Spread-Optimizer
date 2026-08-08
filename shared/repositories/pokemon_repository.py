"""Read and search the nested Pokédex data."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from shared.models.pokemon import Pokemon, PokemonForm
from shared.paths import POKEMON_V2_FILE


def _normalize(value: str) -> str:
    """Normalize user input without discarding meaningful accents."""
    value = unicodedata.normalize("NFKC", value).casefold().strip()
    value = value.replace("♀", " female").replace("♂", " male")
    value = value.replace("_", " ").replace("-", " ")
    value = re.sub(r"[^\w\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


@dataclass(frozen=True, slots=True)
class PokemonMatch:
    pokemon: Pokemon
    form: PokemonForm

    def display_name(self, language: str = "de") -> str:
        if language == "en":
            return self.form.name_en
        return self.form.name_de


class PokemonRepository:
    """Load Pokémon once and offer exact and partial name searches."""

    def __init__(self, file_path: str | Path = POKEMON_V2_FILE) -> None:
        self.file_path = Path(file_path)
        self._pokemon: tuple[Pokemon, ...] = ()
        self._forms: tuple[PokemonMatch, ...] = ()
        self._by_dex: dict[int, Pokemon] = {}
        self._exact_names: dict[str, PokemonMatch] = {}
        self.reload()

    def reload(self) -> None:
        if not self.file_path.is_file():
            raise FileNotFoundError(
                f"Pokédex data not found: {self.file_path}"
            )

        raw_data = json.loads(self.file_path.read_text(encoding="utf-8"))
        if not isinstance(raw_data, list):
            raise ValueError("pokemon_v2.json must contain a JSON list")

        pokemon = tuple(Pokemon.from_dict(item) for item in raw_data)
        by_dex: dict[int, Pokemon] = {}
        forms: list[PokemonMatch] = []
        exact_names: dict[str, PokemonMatch] = {}

        for species in pokemon:
            if species.dex in by_dex:
                raise ValueError(f"Duplicate National Dex number: {species.dex}")
            by_dex[species.dex] = species

            for form in species.forms:
                match = PokemonMatch(species, form)
                forms.append(match)

                names = {
                    form.api_name,
                    form.name_en,
                    form.name_de,
                }
                if form.is_default:
                    names.update(
                        {
                            species.api_name,
                            species.name_en,
                            species.name_de,
                        }
                    )

                for name in names:
                    exact_names.setdefault(_normalize(name), match)

        self._pokemon = pokemon
        self._forms = tuple(forms)
        self._by_dex = by_dex
        self._exact_names = exact_names

    def all_pokemon(self) -> tuple[Pokemon, ...]:
        return self._pokemon

    def all_forms(self) -> tuple[PokemonMatch, ...]:
        return self._forms

    def get_by_dex(self, dex: int) -> Pokemon | None:
        return self._by_dex.get(dex)

    def get_form(self, name: str) -> PokemonMatch | None:
        return self._exact_names.get(_normalize(name))

    def search(
        self,
        query: str,
        *,
        language: str = "de",
        limit: int = 20,
    ) -> list[PokemonMatch]:
        """Return exact, prefix, then substring matches."""
        if limit < 1:
            return []

        normalized_query = _normalize(query)
        if not normalized_query:
            return list(self._forms[:limit])

        ranked: list[tuple[int, int, str, PokemonMatch]] = []

        for match in self._forms:
            names = {
                _normalize(match.form.api_name),
                _normalize(match.form.name_en),
                _normalize(match.form.name_de),
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
                    match.pokemon.dex,
                    _normalize(match.display_name(language)),
                    match,
                )
            )

        ranked.sort(key=lambda item: item[:3])
        return [item[3] for item in ranked[:limit]]
