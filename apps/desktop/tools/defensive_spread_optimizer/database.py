"""Pokémon data adapter for the Defensive Spread Optimizer."""

from __future__ import annotations

from typing import Any

from shared.repositories import PokemonMatch, PokemonRepository


OptimizerPokemon = dict[str, Any]

_repository: PokemonRepository | None = None


def _get_repository() -> PokemonRepository:
    """Return the shared repository, loading its data only once."""
    global _repository

    if _repository is None:
        _repository = PokemonRepository()

    return _repository


def _to_optimizer_pokemon(match: PokemonMatch) -> OptimizerPokemon:
    """Convert a nested Pokédex form into the DSO's flat data format."""
    form = match.form
    stats = form.base_stats

    return {
        "dex": match.pokemon.dex,
        "pokemon_id": form.pokemon_id,
        "api_name": form.api_name,
        "name_en": form.name_en,
        "name_de": form.name_de,
        "sprite_home": form.sprites.home,
        "sprite_home_shiny": form.sprites.home_shiny,
        "base_hp": stats.hp,
        "base_atk": stats.atk,
        "base_def": stats.defense,
        "base_spa": stats.spa,
        "base_spd": stats.spd,
        "base_spe": stats.spe,
    }


def load_pokemon() -> list[OptimizerPokemon]:
    """Return all Pokémon forms in the DSO's flat representation."""
    repository = _get_repository()

    return [
        _to_optimizer_pokemon(match)
        for match in repository.all_forms()
    ]


def get_pokemon(name: str) -> OptimizerPokemon | None:
    """Return one Pokémon form by German, English, or API name."""
    match = _get_repository().get_form(name)

    if match is None:
        return None

    return _to_optimizer_pokemon(match)