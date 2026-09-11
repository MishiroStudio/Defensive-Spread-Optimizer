/// <reference types="node" />

import { readFile } from "node:fs/promises";

import { beforeAll, describe, expect, it } from "vitest";

import type { PokedexBundle } from "../pokedex/pokedex-data";
import { TeamBuilderData, type Item, type TeamBuilderBundle } from "./team-builder-data";
import { parsePokepaste } from "./team-builder-pokepaste";

async function readJson<T>(name: string): Promise<T> {
  const path = new URL(`../../../../../data/${name}.json`, import.meta.url);
  return JSON.parse(await readFile(path, "utf8")) as T;
}

describe("Team Builder production data", () => {
  let data: TeamBuilderData;

  beforeAll(async () => {
    const [pokemon, moves, learnsets, abilities, regulations, items] = await Promise.all([
      readJson<PokedexBundle["pokemon"]>("pokemon_v2"),
      readJson<PokedexBundle["moves"]>("moves"),
      readJson<PokedexBundle["learnsets"]>("learnsets"),
      readJson<PokedexBundle["abilities"]>("abilities"),
      readJson<PokedexBundle["regulations"]>("regulations"),
      readJson<Item[]>("items"),
    ]);
    const bundle: TeamBuilderBundle = { pokemon, moves, learnsets, abilities, regulations, items };
    data = new TeamBuilderData(bundle);
  });

  it("scales Regulation M-B HP to Snorlax's 267", () => {
    expect(data.maximumStats("reg-m-b").hp).toBe(267);
  });

  it("offers Blastoisinite to base Blastoise and selects it for Mega Blastoise", () => {
    const base = data.newMember(data.pokedex.formsByApiName.get("blastoise")!);
    const mega = data.switchForm(base, data.pokedex.formsByApiName.get("blastoise-mega")!.pokemon_id, "reg-m-c");
    expect(data.availableItems(base, "reg-m-c", "de", "mega-stones").map((item) => item.api_name)).toContain("blastoisinite");
    expect(mega.item_id).toBe("blastoisinite");
  });

  it("populates every shared item category and searches item names bilingually", () => {
    const base = data.newMember(data.pokedex.formsByApiName.get("blastoise")!);
    for (const category of ["stat-boost", "power-boost", "defense", "healing", "effect-duration", "berries", "other"] as const) {
      expect(data.availableItems(base, "reg-m-c", "de", category).length, category).toBeGreaterThan(0);
    }
    expect(data.availableItems(base, "reg-m-c", "de", "all", "Life Orb").map((item) => item.name_de)).toContain("Leben-Orb");
  });

  it("resolves the standard Therian names used by PokéPaste", () => {
    const parsed = parsePokepaste([
      "Rain (Tornadus-Therian)",
      "Ability: Regenerator",
      "- Bleakwind Storm",
      "",
      "Landorus-Therian",
      "Ability: Intimidate",
      "- Earthquake",
    ].join("\n"), "national_dex", data);
    expect(parsed.members.map((member) => member.pokemon_api_name)).toEqual(["tornadus-therian", "landorus-therian"]);
  });
});
