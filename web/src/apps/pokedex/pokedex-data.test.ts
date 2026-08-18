import { describe, expect, it } from "vitest";

import { calculateStat, matchRank, normalize } from "./pokedex-data";

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
});
