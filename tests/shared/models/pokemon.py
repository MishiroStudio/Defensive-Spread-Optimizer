"""Typed models for ``data/pokemon_v2.json``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class BaseStats:
    hp: int
    atk: int
    defense: int
    spa: int
    spd: int
    spe: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BaseStats":
        return cls(
            hp=int(data["hp"]),
            atk=int(data["atk"]),
            defense=int(data["def"]),
            spa=int(data["spa"]),
            spd=int(data["spd"]),
            spe=int(data["spe"]),
        )


@dataclass(frozen=True, slots=True)
class Ability:
    api_name: str
    name_en: str
    name_de: str
    is_hidden: bool
    slot: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Ability":
        return cls(
            api_name=str(data["api_name"]),
            name_en=str(data["name_en"]),
            name_de=str(data["name_de"]),
            is_hidden=bool(data["is_hidden"]),
            slot=int(data["slot"]),
        )


@dataclass(frozen=True, slots=True)
class Sprites:
    home: str | None
    home_shiny: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Sprites":
        return cls(
            home=data.get("home"),
            home_shiny=data.get("home_shiny"),
        )


@dataclass(frozen=True, slots=True)
class PokemonForm:
    pokemon_id: int
    api_name: str
    name_en: str
    name_de: str
    is_default: bool
    types: tuple[str, ...]
    base_stats: BaseStats
    abilities: tuple[Ability, ...]
    sprites: Sprites

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PokemonForm":
        return cls(
            pokemon_id=int(data["pokemon_id"]),
            api_name=str(data["api_name"]),
            name_en=str(data["name_en"]),
            name_de=str(data["name_de"]),
            is_default=bool(data["is_default"]),
            types=tuple(str(item) for item in data["types"]),
            base_stats=BaseStats.from_dict(data["base_stats"]),
            abilities=tuple(
                Ability.from_dict(item) for item in data["abilities"]
            ),
            sprites=Sprites.from_dict(data["sprites"]),
        )


@dataclass(frozen=True, slots=True)
class Pokemon:
    dex: int
    api_name: str
    name_en: str
    name_de: str
    forms: tuple[PokemonForm, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Pokemon":
        forms = tuple(PokemonForm.from_dict(item) for item in data["forms"])
        if not forms:
            raise ValueError(f"Pokémon #{data.get('dex', '?')} has no forms")

        return cls(
            dex=int(data["dex"]),
            api_name=str(data["api_name"]),
            name_en=str(data["name_en"]),
            name_de=str(data["name_de"]),
            forms=forms,
        )

    @property
    def default_form(self) -> PokemonForm:
        return next(
            (form for form in self.forms if form.is_default),
            self.forms[0],
        )

