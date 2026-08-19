import { describe, expect, it } from "vitest";

import {
  MAX_TOTAL_STAT_POINTS,
  calculateStat,
  defensiveBulk,
  matchRank,
  normalize,
  statTotal,
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

  it("calculates BST, defensive bulk, and the shared point budget", () => {
    const stats = { hp: 80, atk: 82, def: 83, spa: 100, spd: 100, spe: 80 };

    expect(statTotal(stats)).toBe(525);
    expect(defensiveBulk(stats)).toBe(263);
    expect(MAX_TOTAL_STAT_POINTS).toBe(66);
  });
});