// speed-tier-trainer.test.ts — Speed Tier Trainer PWA V2
import { describe, expect, it } from "vitest";

import type {
  PokemonSpecies,
  RawPokemonForm,
} from "../pokedex/pokedex-data";
import {
  TrainerCatalog,
  TrainerSession,
  USAGE_LIMITS,
  calculateSpeedValues,
  type TrainerBundle,
  type UsageDataset,
} from "./speed-tier-trainer-data";

function form(
  pokemonId: number,
  apiName = `pokemon-${pokemonId}`,
  speed = pokemonId,
): RawPokemonForm {
  return {
    pokemon_id: pokemonId,
    api_name: apiName,
    name_en: apiName,
    name_de: apiName,
    is_default: true,
    types: ["normal"],
    base_stats: { hp: 80, atk: 80, def: 80, spa: 80, spd: 80, spe: speed },
    abilities: [],
    sprites: { home: null, home_shiny: null },
  };
}

function usageDataset(
  formatId: string,
  pokemonIds: number[],
): UsageDataset {
  return {
    format_id: formatId,
    month: "2026-10",
    rating_cutoff: 1760,
    total_battles: 12_345,
    source_url: "https://example.invalid/usage.txt",
    entries: pokemonIds.map((pokemonId, index) => ({
      rank: index + 1,
      pokemon_id: pokemonId,
      api_name: `pokemon-${pokemonId}`,
      showdown_id: `pokemon${pokemonId}`,
      showdown_name: `Pokemon ${pokemonId}`,
      usage_percent: 20 - index,
    })),
  };
}

function bundle(): TrainerBundle {
  const regularSpecies: PokemonSpecies[] = Array.from({ length: 30 }, (_, index) => {
    const pokemonId = index + 1;
    return {
      dex: pokemonId,
      api_name: `pokemon-${pokemonId}`,
      name_en: `Pokemon ${pokemonId}`,
      name_de: `Pokémon ${pokemonId}`,
      evolves_from_species_id: null,
      forms: [form(pokemonId)],
    };
  });
  const floette: PokemonSpecies = {
    dex: 670,
    api_name: "floette",
    name_en: "Floette",
    name_de: "Floette",
    evolves_from_species_id: 669,
    forms: [
      form(670, "floette", 52),
      form(10061, "floette-eternal", 92),
      form(10296, "floette-mega", 102),
    ],
  };
  const currentIds = [
    ...regularSpecies.map((species) => species.forms[0].pokemon_id),
    ...floette.forms.map((pokemon) => pokemon.pokemon_id),
  ];
  const currentUsageIds = [...regularSpecies]
    .reverse()
    .map((species) => species.forms[0].pokemon_id);

  return {
    pokemon: [...regularSpecies, floette],
    regulations: {
      current_regulation_id: "reg-m-c",
      regulations: [
        {
          id: "reg-m-a",
          name: "Regulation M-A",
          status: "expired",
          year: 2026,
          code: "M-A",
          pokemon_ids: [1, 2],
        },
        {
          id: "reg-m-c",
          name: "Regulation M-C",
          status: "current",
          year: 2026,
          code: "M-C",
          pokemon_ids: currentIds,
        },
        {
          id: "reg-m-b",
          name: "Regulation M-B",
          status: "expired",
          year: 2026,
          code: "M-B",
          pokemon_ids: [1, 2, 3],
        },
      ],
    },
    usage: {
      schema_version: 1,
      current_regulation_id: "reg-m-c",
      formats: {
        "reg-m-c": usageDataset("reg-m-c", currentUsageIds),
        "reg-m-b": usageDataset("reg-m-b", [3, 2, 1]),
        "reg-m-a": usageDataset("reg-m-a", [2, 1]),
      },
    },
  };
}

describe("Speed Tier Trainer catalog", () => {
  it("orders the current regulation, National Dex, and history", () => {
    const catalog = new TrainerCatalog(bundle());

    expect(catalog.scopes.map((scope) => scope.key)).toEqual([
      "reg-m-c",
      "all",
      "reg-m-b",
      "reg-m-a",
    ]);
  });

  it("uses the ranked Showdown pool for Top 10, Top 25, and National Dex", () => {
    const catalog = new TrainerCatalog(bundle());
    const expectedTop10 = [30, 29, 28, 27, 26, 25, 24, 23, 22, 21];
    const expectedTop25 = Array.from({ length: 25 }, (_, index) => 30 - index);

    expect(catalog.entriesForScope("reg-m-c", 10).map((entry) => entry.pokemon_id))
      .toEqual(expectedTop10);
    expect(catalog.entriesForScope("all", 10).map((entry) => entry.pokemon_id))
      .toEqual(expectedTop10);
    expect(catalog.entriesForScope("reg-m-c", 25).map((entry) => entry.pokemon_id))
      .toEqual(expectedTop25);
    expect(USAGE_LIMITS).toEqual([100, 50, 25, 10]);
  });

  it("offers Floette's Eternal Flower and Mega forms together", () => {
    const catalog = new TrainerCatalog(bundle());
    const eternal = catalog.entryById(10061)!;

    expect(catalog.megaVariants(eternal, "reg-m-c").map((entry) => entry.api_name))
      .toEqual(["floette-eternal", "floette-mega"]);
  });
});

describe("Speed Tier Trainer calculations and session", () => {
  it("matches the level-50 minimum and maximum table", () => {
    expect(calculateSpeedValues(50)).toEqual({
      minimumNeutral: 70,
      minimumDecreased: 63,
      maximumNeutral: 102,
      maximumIncreased: 112,
      choiceScarfNeutral: 153,
      choiceScarfIncreased: 168,
    });
  });

  it("recalculates an answered question immediately after a Mega form switch", () => {
    const base = { ...form(1, "base", 80), national_dex: 1, evolves_from_species_id: null };
    const mega = { ...form(2, "base-mega", 100), national_dex: 1, evolves_from_species_id: null };
    const session = new TrainerSession([base], { random: () => 0 });

    expect(session.submit(80, base)).toMatchObject({
      pokemon: base,
      difference: 0,
      direction: "exact",
    });
    expect(session.exact).toBe(1);
    expect(session.accuracy).toBe(1);

    expect(session.recalculateCurrentResult(mega)).toMatchObject({
      pokemon: mega,
      guess: 80,
      difference: -20,
      direction: "low",
    });
    expect(session.exact).toBe(0);
    expect(session.incorrectPokemon).toEqual([mega]);
    expect(() => session.submit(100, mega)).toThrow();

    session.advance();
    expect(session.submit(null)).toMatchObject({
      difference: null,
      direction: "revealed",
    });
    expect(session.answered).toBe(2);
    expect(session.guessed).toBe(1);
    expect(session.currentStreak).toBe(0);
  });

  it("finishes a limited round and exposes only its incorrect Pokémon", () => {
    const pokemon = [1, 2, 3].map((id) => ({
      ...form(id, `pokemon-${id}`, 50 + id),
      national_dex: id,
      evolves_from_species_id: null,
    }));
    const session = new TrainerSession(pokemon, { finite: true, random: () => 0 });

    session.submit(session.current.base_stats.spe);
    session.advance();
    const firstIncorrect = session.current;
    session.submit(1);
    session.advance();
    const secondIncorrect = session.current;
    session.submit(null);

    expect(session.isComplete).toBe(true);
    expect(session.exact).toBe(1);
    expect(session.incorrectPokemon).toEqual([firstIncorrect, secondIncorrect]);
    expect(session.roundPokemon).toEqual(pokemon);
    expect(() => session.advance()).toThrow("Runde ist bereits abgeschlossen");
  });

  it("runs endlessly without repeats inside a deck or at its boundary", () => {
    const pokemon = [1, 2, 3].map((id) => ({
      ...form(id),
      national_dex: id,
      evolves_from_species_id: null,
    }));
    const session = new TrainerSession(pokemon, { random: () => 0 });
    const firstDeck: number[] = [];

    for (let index = 0; index < pokemon.length; index += 1) {
      firstDeck.push(session.current.pokemon_id);
      session.submit(null);
      session.advance();
    }

    expect(new Set(firstDeck).size).toBe(pokemon.length);
    expect(session.current.pokemon_id).not.toBe(firstDeck.at(-1));
  });
});
