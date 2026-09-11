import { describe, expect, it } from "vitest";

import type {
  Move,
  PokedexBundle,
  PokemonSpecies,
} from "../pokedex/pokedex-data";
import {
  TeamBuilderData,
  normalizeMember,
  persistedMember,
  type Item,
  type TeamBuilderBundle,
  type TeamSnapshot,
} from "./team-builder-data";
import {
  exportPokepaste,
  parsePokepaste,
  parseStatPoints,
} from "./team-builder-pokepaste";
import {
  emptyTeamLibrary,
  normalizeTeamLibrary,
  upsertTeam,
} from "./team-builder-storage";
import { moveRosterMember } from "./team-builder-roster";

const pokemon: PokemonSpecies[] = [{
  dex: 9,
  api_name: "blastoise",
  name_en: "Blastoise",
  name_de: "Turtok",
  evolves_from_species_id: 8,
  forms: [
    {
      pokemon_id: 9,
      api_name: "blastoise",
      name_en: "Blastoise",
      name_de: "Turtok",
      is_default: true,
      types: ["water"],
      base_stats: { hp: 79, atk: 83, def: 100, spa: 85, spd: 105, spe: 78 },
      abilities: [
        { api_name: "torrent", name_en: "Torrent", name_de: "Sturzbach", is_hidden: false, slot: 1 },
        { api_name: "rain-dish", name_en: "Rain Dish", name_de: "Regengenuss", is_hidden: true, slot: 3 },
      ],
      sprites: { home: null, home_shiny: null },
    },
    {
      pokemon_id: 10036,
      api_name: "blastoise-mega",
      name_en: "Blastoise (Mega)",
      name_de: "Turtok (Mega)",
      is_default: false,
      types: ["water"],
      base_stats: { hp: 79, atk: 103, def: 120, spa: 135, spd: 115, spe: 78 },
      abilities: [{ api_name: "mega-launcher", name_en: "Mega Launcher", name_de: "Megawumme", is_hidden: false, slot: 1 }],
      sprites: { home: null, home_shiny: null },
    },
  ],
}];

const moves: Move[] = [{
  move_id: 56,
  api_name: "hydro-pump",
  name_en: "Hydro Pump",
  name_de: "Hydropumpe",
  type: "water",
  category: "special",
  power: 110,
  accuracy: 80,
  always_hits: false,
  pp: 5,
  priority: 0,
  properties: [],
  effects: { summary_en: "No additional effect.", summary_de: "Kein zusätzlicher Effekt." },
}];

const items: Item[] = [{
  item_id: 761,
  api_name: "blastoisinite",
  showdown_id: "blastoisinite",
  name_en: "Blastoisinite",
  name_de: "Turtoknit",
  description_en: "Allows Blastoise to Mega Evolve.",
  description_de: "Ermöglicht Turtok die Mega-Entwicklung.",
  category: "mega-stones",
  restricted_to: ["blastoise"],
  mega_stone: { blastoise: "blastoisemega" },
  legal_in_regulations: ["reg-m-c"],
  effect_categories: ["mega-stones"],
}];

function bundle(): TeamBuilderBundle {
  const base: PokedexBundle = {
    pokemon,
    moves,
    learnsets: [
      { pokemon_id: 9, api_name: "blastoise", available_in_champions: true, learnset_source: "champions", is_fallback: false, move_ids: [56], note: null },
      { pokemon_id: 10036, api_name: "blastoise-mega", available_in_champions: true, learnset_source: "champions", is_fallback: false, move_ids: [56], note: null },
    ],
    abilities: [
      { ability_id: 67, api_name: "torrent", name_en: "Torrent", name_de: "Sturzbach", description_en: "Boosts Water moves.", description_de: "Verstärkt Wasser-Attacken." },
      { ability_id: 44, api_name: "rain-dish", name_en: "Rain Dish", name_de: "Regengenuss", description_en: "Restores HP in rain.", description_de: "Heilt im Regen KP." },
      { ability_id: 178, api_name: "mega-launcher", name_en: "Mega Launcher", name_de: "Megawumme", description_en: "Boosts pulse moves.", description_de: "Verstärkt Wellen-Attacken." },
    ],
    regulations: {
      current_regulation_id: "reg-m-c",
      regulations: [{ id: "reg-m-c", name: "Regulation M-C", status: "current", format_name: "[Gen 9 Champions] VGC 2026 Reg M-C", mod: "champions", year: 2026, code: "M-C", pokemon_ids: [9, 10036] }],
    },
  };
  return { ...base, items };
}

describe("Team Builder form handling", () => {
  it("remembers a base ability across a Mega round trip", () => {
    const data = new TeamBuilderData(bundle());
    const base = data.newMember(data.pokedex.formsByPokemonId.get(9)!);
    base.ability_id = "rain-dish";
    base.ability_ids_by_form = { 9: "rain-dish" };

    const mega = data.switchForm(base, 10036, "reg-m-c");
    expect(mega.ability_id).toBe("mega-launcher");
    expect(mega.item_id).toBe("blastoisinite");

    const restored = data.switchForm(mega, 9, "reg-m-c");
    expect(restored.ability_id).toBe("rain-dish");
  });

  it("uses the base identity in compact view and offers its Mega Stone", () => {
    const data = new TeamBuilderData(bundle());
    const base = data.newMember(data.pokedex.formsByPokemonId.get(9)!);
    const mega = data.switchForm(base, 10036, "reg-m-c");

    expect(data.compactDisplayForm(mega).api_name).toBe("blastoise");
    expect(data.availableItems(base, "reg-m-c", "de", "mega-stones").map((item) => item.api_name)).toEqual(["blastoisinite"]);
  });

  it("searches Pokémon and moves in both languages", () => {
    const data = new TeamBuilderData(bundle());
    const member = data.newMember(data.pokedex.formsByPokemonId.get(9)!);
    expect(data.searchForms("Blastoise", "reg-m-c")[0].name_de).toBe("Turtok");
    expect(data.filteredMoves(member, "de", "", "", "Hydro Pump")[0].name_de).toBe("Hydropumpe");
  });

  it("keeps form-specific ability memory in the live clone but not in saved JSON", () => {
    const data = new TeamBuilderData(bundle());
    const member = data.newMember(data.pokedex.formsByPokemonId.get(9)!);
    member.ability_id = "rain-dish";
    member.ability_ids_by_form = { 9: "rain-dish", 10036: "mega-launcher" };

    expect(normalizeMember(member)?.ability_ids_by_form).toEqual(member.ability_ids_by_form);
    expect(persistedMember(member)?.ability_ids_by_form).toBeUndefined();
  });
});

describe("Champions Stat Points and PokéPaste", () => {
  it("limits individual points to 32 and total points to 66", () => {
    expect(parseStatPoints("32 HP / 32 Atk / 32 Def", false)).toEqual({ hp: 32, atk: 32, def: 2, spa: 0, spd: 0, spe: 0 });
    expect(parseStatPoints("252 HP / 252 SpD / 4 Spe", true)).toEqual({ hp: 32, atk: 0, def: 0, spa: 0, spd: 32, spe: 1 });
  });

  it("round-trips direct 0–32 points through the EVs label", () => {
    const data = new TeamBuilderData(bundle());
    const member = data.newMember(data.pokedex.formsByPokemonId.get(9)!);
    member.ability_id = "torrent";
    member.item_id = "blastoisinite";
    member.move_ids = ["hydro-pump"];
    member.stat_points = { hp: 32, atk: 0, def: 2, spa: 32, spd: 0, spe: 0 };
    member.nature_increased = "spa";
    member.nature_decreased = "atk";

    const paste = exportPokepaste([member, null], "reg-m-c", "Regulation M-C", data);
    expect(paste).toContain("EVs: 32 HP / 2 Def / 32 SpA");
    expect(paste).toContain("Format: [Gen 9 Champions] VGC 2026 Reg M-C");

    const parsed = parsePokepaste(paste, "reg-m-c", data);
    expect(parsed.issues).toEqual([]);
    expect(parsed.members[0].stat_points).toEqual(member.stat_points);
    expect(parsed.members[0].move_ids).toEqual(["hydro-pump"]);
  });
});

describe("team folders", () => {
  it("persists all six slots and the complete bench", () => {
    const data = new TeamBuilderData(bundle());
    const member = data.newMember(data.pokedex.formsByPokemonId.get(9)!);
    const document = emptyTeamLibrary("My teams");
    const snapshot: TeamSnapshot = {
      name: "Rain",
      regulation_id: "reg-m-c",
      active_slots: [member, null, null, null, null, null],
      bench: [member, member],
    };
    const [stored] = upsertTeam(document, document.folders[0].id, snapshot);
    const reloaded = normalizeTeamLibrary(JSON.parse(JSON.stringify(stored)), "My teams");

    expect(reloaded.folders[0].teams[0].active_slots).toHaveLength(6);
    expect(reloaded.folders[0].teams[0].bench).toHaveLength(2);
  });
});

describe("roster drag and drop", () => {
  it("swaps an occupied team slot with an occupied bench slot", () => {
    const data = new TeamBuilderData(bundle());
    const base = data.newMember(data.pokedex.formsByPokemonId.get(9)!);
    const mega = data.switchForm(base, 10036, "reg-m-c");
    const state = moveRosterMember(
      [base, null, null, null, null, null],
      [mega],
      { area: "team", index: 0 },
      { area: "bench", index: 0 },
    );
    expect(state.team[0]?.pokemon_api_name).toBe("blastoise-mega");
    expect(state.bench[0].pokemon_api_name).toBe("blastoise");
  });

  it("moves a bench member into an empty team slot", () => {
    const data = new TeamBuilderData(bundle());
    const member = data.newMember(data.pokedex.formsByPokemonId.get(9)!);
    const state = moveRosterMember(
      [null, null, null, null, null, null],
      [member],
      { area: "bench", index: 0 },
      { area: "team", index: 4 },
    );
    expect(state.team[4]?.pokemon_api_name).toBe("blastoise");
    expect(state.bench).toEqual([]);
  });
});
