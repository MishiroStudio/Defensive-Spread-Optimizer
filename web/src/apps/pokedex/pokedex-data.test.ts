// pokedex-data.test.ts — Pokédex V10
import { describe, expect, it } from "vitest";

import {
  type Move,
  type PokemonForm,
  MAX_TOTAL_STAT_POINTS,
  RUBRIC_ORDER,
  calculateStat,
  defensiveBulk,
  matchRank,
  moveMatchesRubric,
  normalize,
  relatedMegaForms,
  statTotal,
  toggleNatureModifier,
} from "./pokedex-data";

describe("Pokédex data helpers", () => {
  it("ranks exact, prefix, and substring matches in that order", () => {
    expect(matchRank("Pikachu", ["Pikachu"])).toBe(0);
    expect(matchRank("Pika", ["Pikachu"])).toBe(1);
    expect(matchRank("kachu", ["Pikachu"])).toBe(2);
    expect(matchRank("Eevee", ["Pikachu"])).toBeNull();
  });

  it("normalizes symbols and separators used by Pokémon form names", () => {
    expect(normalize("Nidoran♀_Mega-X")).toBe("nidoran female mega x");
  });

  it("keeps the Champions level-50 stat formula", () => {
    expect(calculateStat("hp", 100, 0, 1)).toBe(175);
    expect(calculateStat("atk", 100, 0, 1)).toBe(120);
    expect(calculateStat("atk", 100, 0, 1.1)).toBe(132);
  });

  it("keeps Shedinja at exactly one HP regardless of invested points", () => {
    expect(calculateStat("hp", 1, 0, 1)).toBe(1);
    expect(calculateStat("hp", 1, 32, 1)).toBe(1);
  });

  it("changes a nature marker only for the selected stat", () => {
    const current = { hp: 1, atk: 1.1, def: 1.1, spa: 1, spd: 0.9, spe: 1 };
    const changed = toggleNatureModifier(current, "atk", 0.9);

    expect(changed).toEqual({ hp: 1, atk: 0.9, def: 1.1, spa: 1, spd: 0.9, spe: 1 });
    expect(toggleNatureModifier(changed, "atk", 0.9).atk).toBe(1);
  });

  it("links base and sibling Mega forms without linking the current form", () => {
    const base = { pokemon_id: 6, api_name: "charizard", is_default: true } as PokemonForm;
    const megaX = { pokemon_id: 10034, api_name: "charizard-mega-x", is_default: false } as PokemonForm;
    const megaY = { pokemon_id: 10035, api_name: "charizard-mega-y", is_default: false } as PokemonForm;
    const forms = [base, megaX, megaY];

    expect(relatedMegaForms(base, forms)).toEqual([megaX, megaY]);
    expect(relatedMegaForms(megaX, forms)).toEqual([base, megaY]);
  });

  it("calculates BST, defensive bulk, and the shared point budget", () => {
    const stats = { hp: 80, atk: 82, def: 83, spa: 100, spd: 100, spe: 80 };

    expect(statTotal(stats)).toBe(525);
    expect(defensiveBulk(stats)).toBe(263);
    expect(MAX_TOTAL_STAT_POINTS).toBe(66);
  });

  it("filters contact moves through the move property supplied by the dataset", () => {
    const contactMove = { properties: ["contact"] } as Move;
    const rangedMove = { properties: ["pulse"] } as Move;

    expect(moveMatchesRubric(contactMove, "contact")).toBe(true);
    expect(moveMatchesRubric(rangedMove, "contact")).toBe(false);
    expect(RUBRIC_ORDER.slice(0, 2)).toEqual(["priority", "contact"]);
  });
});
