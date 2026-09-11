import {
  MAX_STAT_POINTS,
  MAX_TOTAL_STAT_POINTS,
  STAT_ORDER,
  normalize,
  type StatKey,
} from "../pokedex/pokedex-data";
import { EMPTY_STAT_POINTS, TeamBuilderData, type TeamMember } from "./team-builder-data";

const STAT_LABELS: Record<StatKey, string> = {
  hp: "HP",
  atk: "Atk",
  def: "Def",
  spa: "SpA",
  spd: "SpD",
  spe: "Spe",
};

const STAT_ALIASES: Record<string, StatKey> = {
  hp: "hp", kp: "hp",
  atk: "atk", attack: "atk", angr: "atk",
  def: "def", defense: "def", vert: "def",
  spa: "spa", spatk: "spa", specialattack: "spa", spang: "spa",
  spd: "spd", spdef: "spd", specialdefense: "spd", spvert: "spd",
  spe: "spe", speed: "spe", init: "spe",
};

export interface PasteParseResult {
  members: TeamMember[];
  issues: string[];
}

export function parsePasteId(value: string): string | null {
  const clean = value.trim();
  const identifier = "(?:[0-9a-f]{16}|[0-9]{1,10})";
  if (new RegExp(`^${identifier}$`, "i").test(clean)) return clean.toLocaleLowerCase();
  return clean.match(new RegExp(`^(?:https?://)?(?:www\\.)?pokepast\\.es/(${identifier})(?:/(?:raw|json))?/?(?:[?#].*)?$`, "i"))?.[1]?.toLocaleLowerCase() ?? null;
}

export function parseStatPoints(line: string, convertEvs: boolean): Record<StatKey, number> {
  const points = EMPTY_STAT_POINTS();
  line.split("/").forEach((segment) => {
    const match = segment.match(/^\s*(\d+)\s+(.+?)\s*$/);
    if (!match) return;
    const stat = STAT_ALIASES[normalize(match[2]).replaceAll(" ", "")]
      ?? STAT_ALIASES[normalize(match[2])];
    if (!stat) return;
    let value = Number(match[1]);
    if (convertEvs) value = Math.floor((value + 4) / 8);
    points[stat] = Math.max(0, Math.min(MAX_STAT_POINTS, value));
  });
  let overflow = Math.max(0, STAT_ORDER.reduce((sum, stat) => sum + points[stat], 0) - MAX_TOTAL_STAT_POINTS);
  for (const stat of [...STAT_ORDER].reverse()) {
    const reduction = Math.min(points[stat], overflow);
    points[stat] -= reduction;
    overflow -= reduction;
  }
  return points;
}

export function parsePokepaste(paste: string, regulationId: string, data: TeamBuilderData): PasteParseResult {
  const members: TeamMember[] = [];
  const issues: string[] = [];
  const legalItems = new Set(data.legalItems(regulationId, "en").map((item) => item.api_name));
  const blocks = paste.replaceAll("\r\n", "\n").trim().split(/\n\s*\n+/);
  for (const block of blocks) {
    const lines = block.split("\n").map((line) => line.trim()).filter(Boolean);
    if (!lines.length) continue;
    const formatText = lines.slice(1).filter((line) => /^(?:format|regulation):/i.test(line)).map((line) => line.split(":").slice(1).join(":")).join(" ");
    const regulation = data.pokedex.regulationsById.get(regulationId);
    const regulationMod = regulation?.mod?.toLocaleLowerCase() ?? "";
    const championsFormat = regulationMod.startsWith("champions")
      || ["regulation", "regulation-m"].includes(regulationMod)
      || normalize(formatText).includes("champion")
      || normalize(formatText).includes("regulation m");
    const [pokemonHeader, itemText = ""] = lines[0].split("@").map((part) => part.trim());
    const form = data.resolvePasteForm(pokemonHeader, regulationId);
    if (!form) {
      issues.push(pokemonHeader);
      continue;
    }
    const member = data.newMember(form);
    if (itemText) {
      const itemId = data.resolvePasteItem(itemText);
      const item = itemId ? data.itemsByName.get(itemId) : undefined;
      if (itemId && item && legalItems.has(itemId) && data.megaStoneMatches(item, member)) member.item_id = itemId;
      else issues.push(`${pokemonHeader}: ${itemText}`);
    }
    for (const line of lines.slice(1)) {
      if (/^ability:/i.test(line)) {
        const value = line.split(":").slice(1).join(":").trim();
        const ability = data.resolvePasteAbility(member, value);
        if (ability) member.ability_id = ability;
        else issues.push(`${pokemonHeader}: ${value}`);
      } else if (/^stat points:/i.test(line)) {
        member.stat_points = parseStatPoints(line.split(":").slice(1).join(":"), false);
      } else if (/^evs:/i.test(line)) {
        const values = line.split(":").slice(1).join(":");
        const numeric = [...values.matchAll(/\b(\d+)\s+[A-Za-z]+/g)].map((match) => Number(match[1]));
        member.stat_points = parseStatPoints(values, !(championsFormat && numeric.every((value) => value <= MAX_STAT_POINTS)));
      } else if (line.startsWith("-")) {
        const value = line.slice(1).trim().split("/")[0].trim();
        const move = data.resolvePasteMove(member, value);
        if (move && !member.move_ids.includes(move) && member.move_ids.length < 4) member.move_ids.push(move);
        else if (value) issues.push(`${pokemonHeader}: ${value}`);
      } else {
        const match = line.match(/^(.+?)\s+Nature$/i);
        if (match) {
          const nature = data.resolveNature(match[1]);
          if (nature) [member.nature_increased, member.nature_decreased] = nature;
        }
      }
    }
    if (!member.ability_id && form.abilities.length === 1) member.ability_id = form.abilities[0].api_name;
    const megaStone = data.megaStoneForSelectedForm(member, regulationId);
    if (megaStone) member.item_id = megaStone.api_name;
    members.push(member);
  }
  return { members, issues };
}

export function exportPokepaste(
  members: Array<TeamMember | null>,
  regulationId: string,
  regulationName: string,
  data: TeamBuilderData,
): string {
  return members.filter((member): member is TeamMember => member !== null).map((member) => {
    const form = data.form(member);
    const item = member.item_id ? data.itemsByName.get(member.item_id) : undefined;
    const lines = [data.canonicalPasteName(form) + (item ? ` @ ${item.name_en}` : "")];
    const ability = form.abilities.find((entry) => entry.api_name === member.ability_id);
    if (ability) lines.push(`Ability: ${ability.name_en}`);
    lines.push("Level: 50");
    lines.push(`Format: ${data.regulationFormatName(regulationId)}`);
    lines.push(`Regulation: ${regulationName || "Champions"}`);
    const points = STAT_ORDER.filter((stat) => member.stat_points[stat] > 0)
      .map((stat) => `${member.stat_points[stat]} ${STAT_LABELS[stat]}`);
    if (points.length) lines.push(`EVs: ${points.join(" / ")}`);
    lines.push(`${data.natureName(member, "en")} Nature`);
    member.move_ids.slice(0, 4).forEach((id) => {
      const move = data.movesByName.get(id);
      if (move) lines.push(`- ${move.name_en}`);
    });
    return lines.join("\r\n");
  }).join("\r\n\r\n");
}

export async function fetchPokepaste(value: string, signal?: AbortSignal): Promise<{ title: string; paste: string }> {
  const id = parsePasteId(value);
  if (!id) throw new Error("Ungültiger PokéPaste-Link oder ungültige Paste-ID.");
  const response = await fetch(`https://pokepast.es/${id}/json`, { signal });
  if (!response.ok) throw new Error(`PokéPaste antwortete mit Status ${response.status}.`);
  const payload = await response.json() as { title?: unknown; paste?: unknown };
  if (typeof payload.paste !== "string") throw new Error("PokéPaste lieferte keinen Teamtext.");
  return { title: String(payload.title ?? "").trim(), paste: payload.paste };
}

export function submitPokepaste(
  paste: string,
  title: string,
  regulationName: string,
): void {
  // PokéPaste permits cross-origin reads for /json, but /create is a normal
  // HTML form endpoint. A native form submission therefore avoids a CORS-
  // blocked fetch while preserving the exact same payload as the desktop app.
  const form = document.createElement("form");
  form.method = "post";
  form.action = "https://pokepast.es/create";
  form.target = "_blank";
  form.hidden = true;
  const values = {
    paste,
    title: title.trim() || "MISHIRO Team",
    author: "MISHIRO Team Builder",
    notes: `${regulationName} · Champions · MISHIRO Web`,
  };
  Object.entries(values).forEach(([name, value]) => {
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = name;
    input.value = value;
    form.append(input);
  });
  document.body.append(form);
  form.submit();
  form.remove();
}
