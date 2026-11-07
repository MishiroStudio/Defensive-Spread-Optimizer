"""Quiz and data model for the Speed Tier Trainer — version 7."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import random
from typing import Sequence

from shared.calculations.stats import (
    DECREASED_NATURE,
    INCREASED_NATURE,
    MAX_STAT_POINTS,
    NEUTRAL_NATURE,
    calculate_other_stat,
)
from shared.paths import DATA_DIR
from shared.repositories import (
    PokemonRepository,
    UsageDataset,
    UsageRepository,
)


REGULATIONS_FILE = DATA_DIR / "regulations.json"
MEGA_BASE_OVERRIDES = {
    "floette-mega": "floette-eternal",
    "pyroar-mega": "pyroar-male",
}


@dataclass(frozen=True, slots=True)
class QuizPokemon:
    """The small subset of a Pokémon form required by the trainer."""

    pokemon_id: int
    national_dex: int
    api_name: str
    name_de: str
    name_en: str
    base_speed: int
    sprite_path: str | None

    def display_name(self, language: str) -> str:
        return self.name_en if language == "en" else self.name_de


@dataclass(frozen=True, slots=True)
class TrainerScope:
    key: str
    label_de: str
    label_en: str
    pokemon_ids: frozenset[int]

    def label(self, language: str) -> str:
        return self.label_en if language == "en" else self.label_de


@dataclass(frozen=True, slots=True)
class AnswerResult:
    pokemon: QuizPokemon
    guess: int | None
    difference: int | None

    @property
    def is_exact(self) -> bool:
        return self.difference == 0

    @property
    def direction(self) -> str:
        if self.difference is None:
            return "revealed"
        if self.difference < 0:
            return "low"
        if self.difference > 0:
            return "high"
        return "exact"


@dataclass(frozen=True, slots=True)
class SpeedValues:
    """Level-50 Speed values at minimum and maximum investment."""

    minimum_neutral: int
    minimum_decreased: int
    maximum_neutral: int
    maximum_increased: int


def calculate_speed_values(base_speed: int) -> SpeedValues:
    """Return the four useful Champions Speed benchmarks."""
    return SpeedValues(
        minimum_neutral=calculate_other_stat(
            base_speed,
            0,
            NEUTRAL_NATURE,
        ),
        minimum_decreased=calculate_other_stat(
            base_speed,
            0,
            DECREASED_NATURE,
        ),
        maximum_neutral=calculate_other_stat(
            base_speed,
            MAX_STAT_POINTS,
            NEUTRAL_NATURE,
        ),
        maximum_increased=calculate_other_stat(
            base_speed,
            MAX_STAT_POINTS,
            INCREASED_NATURE,
        ),
    )


class TrainerCatalog:
    """Load the shared Pokémon data and create useful quiz pools."""

    def __init__(
        self,
        repository: PokemonRepository | None = None,
        usage_repository: UsageRepository | None = None,
        regulations_file: str | Path = REGULATIONS_FILE,
    ) -> None:
        repository = repository or PokemonRepository()
        entries = [
            QuizPokemon(
                pokemon_id=match.form.pokemon_id,
                national_dex=match.pokemon.dex,
                api_name=match.form.api_name,
                name_de=match.form.name_de,
                name_en=match.form.name_en,
                base_speed=match.form.base_stats.spe,
                sprite_path=match.form.sprites.home,
            )
            for match in repository.all_forms()
        ]
        entries.sort(
            key=lambda pokemon: (
                pokemon.national_dex,
                pokemon.pokemon_id,
            )
        )
        if not entries:
            raise ValueError("pokemon_v2.json contains no Pokémon forms")

        self.entries = tuple(entries)
        self._by_id = {pokemon.pokemon_id: pokemon for pokemon in entries}
        self.usage_repository = usage_repository or UsageRepository()
        self.scopes = self._load_scopes(Path(regulations_file))

    def _load_scopes(self, regulations_file: Path) -> tuple[TrainerScope, ...]:
        if not regulations_file.is_file():
            raise FileNotFoundError(
                f"Regulation data not found: {regulations_file}"
            )
        try:
            data = json.loads(regulations_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Invalid JSON in {regulations_file}: {error}"
            ) from error
        if not isinstance(data, dict) or not isinstance(
            data.get("regulations"),
            list,
        ):
            raise ValueError("regulations.json contains an invalid structure")

        known_ids = frozenset(self._by_id)
        parsed: list[
            tuple[str, str, str, int, frozenset[int]]
        ] = []
        for record in data["regulations"]:
            if not isinstance(record, dict):
                continue
            record_id = record.get("id")
            pokemon_ids = record.get("pokemon_ids")
            if not isinstance(record_id, str) or not isinstance(
                pokemon_ids,
                list,
            ):
                continue
            legal_ids = frozenset(
                pokemon_id
                for pokemon_id in pokemon_ids
                if isinstance(pokemon_id, int) and pokemon_id in known_ids
            )
            if not legal_ids:
                continue
            record_name = str(record.get("name") or record_id)
            record_code = str(record.get("code") or record_name)
            record_year = (
                int(record["year"])
                if isinstance(record.get("year"), int)
                else 0
            )
            parsed.append(
                (
                    record_id,
                    record_name,
                    record_code,
                    record_year,
                    legal_ids,
                )
            )

        if not parsed:
            raise ValueError("regulations.json contains no usable regulation")

        scopes: list[TrainerScope] = []
        current_id = data.get("current_regulation_id")
        current = next(
            (record for record in parsed if record[0] == current_id),
            None,
        )
        if current is None:
            current = max(parsed, key=lambda record: (record[3], record[2]))

        current_record_id, _name, code, _year, pokemon_ids = current
        scopes.append(
            TrainerScope(
                key=current_record_id,
                label_de=f"Regulation {code}",
                label_en=f"Regulation {code}",
                pokemon_ids=pokemon_ids,
            )
        )
        scopes.append(
            TrainerScope(
                key="all",
                label_de="Nationaler Dex",
                label_en="National Dex",
                pokemon_ids=known_ids,
            )
        )

        historical = sorted(
            (
                record
                for record in parsed
                if record[0] != current_record_id
            ),
            key=lambda record: (record[3], record[2]),
            reverse=True,
        )
        for record_id, _name, code, _year, regulation_ids in historical:
            scopes.append(
                TrainerScope(
                    key=record_id,
                    label_de=f"Regulation {code}",
                    label_en=f"Regulation {code}",
                    pokemon_ids=regulation_ids,
                )
            )
        return tuple(scopes)

    def usage_dataset_for_scope(
        self,
        scope_key: str,
    ) -> UsageDataset | None:
        """Return regulation usage; National Dex follows the current format."""
        usage_scope_key = (
            self.scopes[0].key if scope_key == "all" else scope_key
        )
        return self.usage_repository.dataset(usage_scope_key)

    def entries_for_scope(
        self,
        scope_key: str,
        *,
        usage_limit: int | None = None,
    ) -> tuple[QuizPokemon, ...]:
        scope = next(
            (scope for scope in self.scopes if scope.key == scope_key),
            None,
        )
        if scope is None:
            raise KeyError(f"Unknown trainer scope: {scope_key}")
        scope_entries = tuple(
            pokemon
            for pokemon in self.entries
            if pokemon.pokemon_id in scope.pokemon_ids
        )
        if usage_limit is None:
            return scope_entries
        if usage_limit < 1:
            raise ValueError("Usage limit must be at least 1")

        dataset = self.usage_dataset_for_scope(scope_key)
        if dataset is None:
            raise ValueError(
                f"No usage data is available for trainer scope {scope_key!r}"
            )
        entries_by_id = {
            pokemon.pokemon_id: pokemon for pokemon in scope_entries
        }
        ranked_entries: list[QuizPokemon] = []
        for usage_entry in dataset.entries:
            pokemon = entries_by_id.get(usage_entry.pokemon_id)
            if pokemon is None:
                continue
            ranked_entries.append(pokemon)
            if len(ranked_entries) == usage_limit:
                break
        if not ranked_entries:
            raise ValueError(
                f"Usage data and trainer scope {scope_key!r} do not overlap"
            )
        return tuple(ranked_entries)

    def mega_variants(
        self,
        pokemon: QuizPokemon,
        scope_key: str,
    ) -> tuple[QuizPokemon, ...]:
        """Return the selectable base and Mega forms for one question."""
        scope_entries = self.entries_for_scope(scope_key)
        entries_by_api_name = {
            entry.api_name: entry for entry in scope_entries
        }

        if "-mega" in pokemon.api_name:
            base_api_name = MEGA_BASE_OVERRIDES.get(
                pokemon.api_name,
                pokemon.api_name.split("-mega", 1)[0],
            )
        else:
            base_api_name = pokemon.api_name

        base_form = entries_by_api_name.get(base_api_name)
        if base_form is None:
            return (pokemon,)

        mega_forms = sorted(
            (
                entry
                for entry in scope_entries
                if "-mega" in entry.api_name
                and MEGA_BASE_OVERRIDES.get(
                    entry.api_name,
                    entry.api_name.split("-mega", 1)[0],
                )
                == base_api_name
            ),
            key=lambda entry: entry.api_name,
        )
        variants = (base_form, *mega_forms)
        if len(variants) < 2 or pokemon not in variants:
            return (pokemon,)
        return variants


class QuizSession:
    """State for one endless Speed Tier Trainer game."""

    def __init__(
        self,
        pokemon: Sequence[QuizPokemon],
        *,
        rng: random.Random | None = None,
    ) -> None:
        if not pokemon:
            raise ValueError("The selected quiz pool is empty")

        self._pool = tuple(pokemon)
        self._rng = rng or random.Random()
        self._deck: list[QuizPokemon] = []
        self._index = 0
        self._answered_current = False

        self.answered = 0
        self.guessed = 0
        self.exact = 0
        self.total_absolute_error = 0
        self.current_streak = 0
        self.best_streak = 0
        self._shuffle_deck()

    def _shuffle_deck(
        self,
        avoid_first: QuizPokemon | None = None,
    ) -> None:
        self._deck = list(self._pool)
        self._rng.shuffle(self._deck)
        if (
            avoid_first is not None
            and len(self._deck) > 1
            and self._deck[0] == avoid_first
        ):
            self._deck[0], self._deck[1] = self._deck[1], self._deck[0]
        self._index = 0

    @property
    def current(self) -> QuizPokemon:
        return self._deck[self._index]

    @property
    def current_answered(self) -> bool:
        return self._answered_current

    @property
    def question_number(self) -> int:
        return self.answered if self._answered_current else self.answered + 1

    @property
    def accuracy(self) -> float:
        return self.exact / self.answered if self.answered else 0.0

    @property
    def mean_absolute_error(self) -> float:
        return (
            self.total_absolute_error / self.guessed
            if self.guessed
            else 0.0
        )

    def submit(
        self,
        guess: int | None,
        *,
        pokemon: QuizPokemon | None = None,
    ) -> AnswerResult:
        if self._answered_current:
            raise RuntimeError("The current question is already answered")
        if guess is not None and not 1 <= guess <= 255:
            raise ValueError("The answer must be between 1 and 255")

        target = pokemon or self.current
        difference = None if guess is None else guess - target.base_speed
        self.answered += 1
        if difference is not None:
            self.guessed += 1
            self.total_absolute_error += abs(difference)
        if difference == 0:
            self.exact += 1
            self.current_streak += 1
            self.best_streak = max(self.best_streak, self.current_streak)
        else:
            self.current_streak = 0
        self._answered_current = True
        return AnswerResult(
            pokemon=target,
            guess=guess,
            difference=difference,
        )

    def advance(self) -> bool:
        """Advance, reshuffling only after the complete pool was shown."""
        if not self._answered_current:
            raise RuntimeError("The current question is not answered")

        previous = self.current
        self._index += 1
        if self._index >= len(self._deck):
            self._shuffle_deck(avoid_first=previous)
        self._answered_current = False
        return True

