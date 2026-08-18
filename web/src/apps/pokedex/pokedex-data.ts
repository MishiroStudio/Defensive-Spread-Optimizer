import { publicPath } from "./public-path";

export type Language = "de" | "en";
export type StatKey = "hp" | "atk" | "def" | "spa" | "spd" | "spe";
export type MoveCategory = "physical" | "special" | "status";
export type FilterKind = "type" | "ability" | "move";
export type MoveRubric =
  | "priority"
  | "punch"
  | "sound"
  | "dance"
  | "slicing"
  | "wind"
  | "powder"
  | "bullet"
  | "pulse"
  | "bite"
  | "explosion"
  | "mental"
  | "heal";

export interface BaseStats {
  hp: number;
  atk: number;
  def: number;
  spa: number;
  spd: number;
  spe: number;
}

export interface PokemonAbility {
  api_name: string;
  name_en: string;
  name_de: string;
  is_hidden: boolean;
  slot: number;
}

export interface PokemonSprites {
  home: string | null;
  home_shiny: string | null;
}

export interface RawPokemonForm {
  pokemon_id: number;
  api_name: string;
  name_en: string;
  name_de: string;
  is_default: boolean;
  types: string[];
  base_stats: BaseStats;
  abilities: PokemonAbility[];
  sprites: PokemonSprites;
}

export interface PokemonForm extends RawPokemonForm {
  national_dex: number;
  evolves_from_species_id: number | null;
}

export interface PokemonSpecies {
  dex: number;
  api_name: string;
  name_en: string;
  name_de: string;
  evolves_from_species_id: number | null;
  forms: RawPokemonForm[];
}

export interface MoveEffects {
  summary_en?: string | null;
  summary_de?: string | null;
  summary_de_is_fallback?: boolean;
  has_custom_logic?: boolean;
  [key: string]: unknown;
}

export interface Move {
  move_id: number;
  api_name: string;
  name_en: string;
  name_de: string;
  name_de_is_fallback?: boolean;
  type: string;
  category: MoveCategory;
  power: number | null;
  accuracy: number | null;
  always_hits: boolean;
  pp: number;
  max_pp?: number;
  pp_ups_allowed?: boolean;
  pp_by_source?: Record<string, number>;
  priority: number;
  target?: string;
  properties: string[];
  is_spread_move?: boolean;
  effects?: MoveEffects;
}

export interface Learnset {
  pokemon_id: number;
  api_name: string;
  available_in_champions: boolean;
  learnset_source: string;
  is_fallback: boolean;
  move_ids: number[];
  note: string | null;
}

export interface AbilityRecord {
  ability_id: number;
  api_name: string;
  name_en: string;
  name_de: string;
  description_en: string;
  description_de: string;
}

export interface Regulation {
  id: string;
  name: string;
  status: string;
  pokemon_ids: number[];
}

export interface RegulationsData {
  current_regulation_id: string;
  regulations: Regulation[];
}

export interface PokedexBundle {
  pokemon: PokemonSpecies[];
  moves: Move[];
  learnsets: Learnset[];
  abilities: AbilityRecord[];
  regulations: RegulationsData;
}

export interface ActiveFilter {
  kind: FilterKind;
  value: string | number;
}

export interface ScopeEntities {
  types: Set<string>;
  abilities: Set<string>;
  moves: Set<number>;
}

export const ORANGE = "#F28C28";
export const MAX_STAT_POINTS = 32;
export const STAT_ORDER: StatKey[] = ["hp", "atk", "def", "spa", "spd", "spe"];
export const TYPE_ORDER = [
  "normal",
  "grass",
  "fire",
  "water",
  "electric",
  "bug",
  "flying",
  "rock",
  "poison",
  "ground",
  "ice",
  "fighting",
  "psychic",
  "ghost",
  "dragon",
  "dark",
  "steel",
  "fairy",
] as const;

export const TYPE_COLORS: Record<string, string> = {
  normal: "#9FA19F",
  grass: "#3FA129",
  fire: "#E62829",
  water: "#2980EF",
  electric: "#FAC000",
  bug: "#91A119",
  flying: "#81B9EF",
  rock: "#AFA981",
  poison: "#9141CB",
  ground: "#915121",
  ice: "#3FD8FF",
  fighting: "#FF8000",
  psychic: "#EF4179",
  ghost: "#704170",
  dragon: "#5060E1",
  dark: "#50413F",
  steel: "#60A1B8",
  fairy: "#EF70EF",
};

export const TYPE_NAMES: Record<Language, Record<string, string>> = {
  de: {
    normal: "Normal",
    fire: "Feuer",
    water: "Wasser",
    electric: "Elektro",
    grass: "Pflanze",
    ice: "Eis",
    fighting: "Kampf",
    poison: "Gift",
    ground: "Boden",
    flying: "Flug",
    psychic: "Psycho",
    bug: "Käfer",
    rock: "Gestein",
    ghost: "Geist",
    dragon: "Drache",
    dark: "Unlicht",
    steel: "Stahl",
    fairy: "Fee",
  },
  en: Object.fromEntries(TYPE_ORDER.map((type) => [
    type,
    `${type.charAt(0).toUpperCase()}${type.slice(1)}`,
  ])),
};

export const STAT_NAMES: Record<Language, Record<StatKey, string>> = {
  de: {
    hp: "KP",
    atk: "Angriff",
    def: "Verteidigung",
    spa: "Sp.-Angriff",
    spd: "Sp.-Verteidigung",
    spe: "Initiative",
  },
  en: {
    hp: "HP",
    atk: "Attack",
    def: "Defense",
    spa: "Sp. Attack",
    spd: "Sp. Defense",
    spe: "Speed",
  },
};

export const CATEGORY_NAMES: Record<Language, Record<MoveCategory, string>> = {
  de: { physical: "Physisch", special: "Speziell", status: "Status" },
  en: { physical: "Physical", special: "Special", status: "Status" },
};

export const CATEGORY_COLORS: Record<MoveCategory, string> = {
  physical: "#D85B45",
  special: "#4A90D9",
  status: "#7A7A7A",
};

export const CATEGORY_ICON_FILES: Record<MoveCategory, string> = {
  physical: "PhysicalIC_CP.png",
  special: "SpecialIC_CP.png",
  status: "StatusIC_CP.png",
};

export const RUBRIC_ORDER: MoveRubric[] = [
  "priority",
  "punch",
  "sound",
  "dance",
  "slicing",
  "wind",
  "powder",
  "bullet",
  "pulse",
  "bite",
  "explosion",
  "mental",
  "heal",
];

export const RUBRIC_NAMES: Record<Language, Record<MoveRubric, string>> = {
  de: {
    priority: "Priorität",
    punch: "Hieb",
    sound: "Geräusch",
    dance: "Tanz",
    slicing: "Schnitt",
    wind: "Wind",
    powder: "Pulver",
    bullet: "Kugelgeschoss",
    pulse: "Impulswellen",
    bite: "Biss",
    explosion: "Explosion",
    mental: "Mental",
    heal: "Heilung",
  },
  en: {
    priority: "Priority",
    punch: "Punch",
    sound: "Sound",
    dance: "Dance",
    slicing: "Slicing",
    wind: "Wind",
    powder: "Powder",
    bullet: "Bullet",
    pulse: "Pulse",
    bite: "Bite",
    explosion: "Explosion",
    mental: "Mental",
    heal: "Healing",
  },
};

export const SOURCE_NAMES: Record<Language, Record<string, string>> = {
  de: {
    champions: "Pokémon Champions",
    "scarlet-violet": "Karmesin/Purpur",
    "sword-shield": "Schwert/Schild",
    bdsp: "Strahlender Diamant/Leuchtende Perle",
  },
  en: {
    champions: "Pokémon Champions",
    "scarlet-violet": "Scarlet/Violet",
    "sword-shield": "Sword/Shield",
    bdsp: "Brilliant Diamond/Shining Pearl",
  },
};

const REGIONAL_TOKENS = ["alola", "galar", "hisui", "paldea"];
const PARENT_FORM_OVERRIDES: Record<string, string> = {
  perrserker: "meowth-galar",
  sirfetchd: "farfetchd-galar",
  cursola: "corsola-galar",
  obstagoon: "linoone-galar",
  runerigus: "yamask-galar",
  "mr-rime": "mr-mime-galar",
  sneasler: "sneasel-hisui",
  overqwil: "qwilfish-hisui",
  "basculegion-male": "basculin-white-striped",
  "basculegion-female": "basculin-white-striped",
  basculegion: "basculin-white-striped",
  clodsire: "wooper-paldea",
};

const EXPLOSION_MOVES = new Set([
  "selfdestruct",
  "explosion",
  "mindblown",
  "mistyexplosion",
]);
const MENTAL_MOVES = new Set([
  "attract",
  "disable",
  "encore",
  "healblock",
  "taunt",
  "torment",
]);

export function normalize(value: string): string {
  return value
    .normalize("NFKC")
    .toLocaleLowerCase()
    .trim()
    .replaceAll("♀", " female")
    .replaceAll("♂", " male")
    .replaceAll("_", " ")
    .replaceAll("-", " ")
    .replace(/[^\p{L}\p{N}_\s]/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function matchRank(query: string, names: string[]): number | null {
  const needle = normalize(query);
  const normalizedNames = [...new Set(names.map(normalize).filter(Boolean))];
  if (!needle || normalizedNames.length === 0) return null;
  if (normalizedNames.includes(needle)) return 0;
  if (normalizedNames.some((name) => name.startsWith(needle))) return 1;
  if (normalizedNames.some((name) => name.includes(needle))) return 2;
  return null;
}

export function localizedName(
  entity: { name_de?: string; name_en?: string; api_name?: string },
  language: Language,
): string {
  return entity[`name_${language}`] || entity.name_en || entity.api_name || "–";
}

export function calculateStat(
  stat: StatKey,
  base: number,
  points = 0,
  nature = 1,
): number {
  if (stat === "hp") {
    return Math.floor((2 * base + 31) / 2) + 60 + points;
  }
  const neutral = Math.floor((2 * base + 31) / 2) + 5 + points;
  return Math.floor(neutral * nature);
}

export function calculateAllStats(
  baseStats: BaseStats,
  points: Record<StatKey, number>,
  natures: Record<StatKey, number>,
): BaseStats {
  return Object.fromEntries(STAT_ORDER.map((stat) => [
    stat,
    calculateStat(stat, baseStats[stat], points[stat], natures[stat]),
  ])) as unknown as BaseStats;
}

export function moveMatchesRubric(move: Move, rubric: MoveRubric | ""): boolean {
  if (!rubric) return true;
  const properties = new Set(move.properties || []);
  if (rubric === "priority") return move.priority !== 0;
  if (rubric === "explosion") {
    return properties.has("explosion") || EXPLOSION_MOVES.has(move.api_name);
  }
  if (rubric === "mental") {
    return properties.has("mental") || MENTAL_MOVES.has(move.api_name);
  }
  return properties.has(rubric);
}

export function moveDisplayPp(move: Move, source: string | undefined): string {
  const sourcePp = source ? move.pp_by_source?.[source] : undefined;
  if (typeof sourcePp === "number") return String(Math.trunc(sourcePp));
  if (typeof move.pp !== "number") return "–";
  if (source === "champions") {
    const capped = Math.min(move.pp, 20);
    return String(move.pp_ups_allowed === false ? capped : (capped / 5 + 1) * 4);
  }
  return String(Math.trunc(move.pp));
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

function fractionPercent(value: unknown): string | null {
  if (!Array.isArray(value) || value.length !== 2) return null;
  const [numerator, denominator] = value;
  if (typeof numerator !== "number" || typeof denominator !== "number" || denominator === 0) {
    return null;
  }
  const percentage = numerator / denominator * 100;
  return Number.isInteger(percentage) ? `${percentage}%` : `${Number(percentage.toPrecision(4))}%`;
}

function joinWords(values: string[], language: Language): string {
  if (values.length < 2) return values[0] ?? "";
  const conjunction = language === "de" ? "und" : "and";
  if (values.length === 2) return `${values[0]} ${conjunction} ${values[1]}`;
  return `${values.slice(0, -1).join(", ")} ${conjunction} ${values.at(-1)}`;
}

const EFFECT_STAT_NAMES: Record<Language, Record<string, string>> = {
  de: {
    atk: "Angriff",
    def: "Verteidigung",
    spa: "Sp.-Ang.",
    spd: "Sp.-Vert.",
    spe: "Initiative",
    accuracy: "Genauigkeit",
    evasion: "Ausweichwert",
  },
  en: {
    atk: "Attack",
    def: "Defense",
    spa: "Sp. Atk",
    spd: "Sp. Def",
    spe: "Speed",
    accuracy: "Accuracy",
    evasion: "Evasion",
  },
};

function formatStatChanges(
  rawChanges: unknown,
  subject: "user" | "target" | "foes",
  language: Language,
): string[] {
  const changes = asRecord(rawChanges);
  const grouped = new Map<number, string[]>();
  for (const [stat, amount] of Object.entries(changes)) {
    if (typeof amount !== "number" || amount === 0) continue;
    const integer = Math.trunc(amount);
    grouped.set(integer, [...(grouped.get(integer) ?? []), EFFECT_STAT_NAMES[language][stat] ?? stat]);
  }
  return [...grouped].map(([amount, stats]) => {
    const magnitude = Math.abs(amount);
    const statText = joinWords(stats, language);
    if (language === "de") {
      const subjectText = subject === "user"
        ? "des Anwenders"
        : subject === "foes" ? "gegnerischer Pokémon" : "des Ziels";
      return `${amount > 0 ? "Erhöht" : "Senkt"} ${statText} ${subjectText} um ${magnitude} ${magnitude === 1 ? "Stufe" : "Stufen"}.`;
    }
    const subjectText = subject === "user"
      ? "the user's"
      : subject === "foes" ? "opposing Pokémon's" : "the target's";
    return `${amount > 0 ? "Raises" : "Lowers"} ${subjectText} ${statText} by ${magnitude} ${magnitude === 1 ? "stage" : "stages"}.`;
  });
}

function formatStatus(
  status: string,
  chance: number | null,
  language: Language,
): string | null {
  const direct: Record<Language, Record<string, string>> = {
    de: {
      brn: "Verbrennt das Ziel.",
      par: "Paralysiert das Ziel.",
      psn: "Vergiftet das Ziel.",
      slp: "Lässt das Ziel einschlafen.",
      tox: "Vergiftet das Ziel schwer.",
      frz: "Friert das Ziel ein.",
    },
    en: {
      brn: "Burns the target.",
      par: "Paralyzes the target.",
      psn: "Poisons the target.",
      slp: "Puts the target to sleep.",
      tox: "Badly poisons the target.",
      frz: "Freezes the target.",
    },
  };
  const chanceAction: Record<Language, Record<string, string>> = {
    de: {
      brn: "das Ziel zu verbrennen",
      par: "das Ziel zu paralysieren",
      psn: "das Ziel zu vergiften",
      slp: "das Ziel einschlafen zu lassen",
      tox: "das Ziel schwer zu vergiften",
      frz: "das Ziel einzufrieren",
    },
    en: {
      brn: "burn the target",
      par: "paralyze the target",
      psn: "poison the target",
      slp: "put the target to sleep",
      tox: "badly poison the target",
      frz: "freeze the target",
    },
  };
  const action = chanceAction[language][status];
  if (!action) return null;
  if (chance !== null) {
    return language === "de"
      ? `${chance}% Chance, ${action}.`
      : `${chance}% chance to ${action}.`;
  }
  return direct[language][status];
}

const VOLATILE_TEXT: Record<Language, Record<string, string>> = {
  de: {
    confusion: "Verwirrt das Ziel.",
    partiallytrapped: "Fängt das Ziel.",
    leechseed: "Belegt das Ziel mit Egelsamen.",
    disable: "Blockiert die zuletzt eingesetzte Attacke des Ziels.",
    taunt: "Versetzt das Ziel in den Verhöhner-Zustand.",
    encore: "Zwingt das Ziel, seine letzte Attacke zu wiederholen.",
    yawn: "Macht das Ziel schläfrig.",
    attract: "Macht das Ziel vernarrt.",
    substitute: "Erzeugt einen Delegator.",
    protect: "Schützt den Anwender.",
    endure: "Der Anwender überlebt mit mindestens 1 KP.",
    ingrain: "Verwurzelt den Anwender.",
    aquaring: "Umhüllt den Anwender mit Wasserring.",
  },
  en: {
    confusion: "Confuses the target.",
    partiallytrapped: "Traps the target.",
    leechseed: "Seeds the target with Leech Seed.",
    disable: "Disables the target's last move.",
    taunt: "Taunts the target.",
    encore: "Forces the target to repeat its last move.",
    yawn: "Makes the target drowsy.",
    attract: "Infatuates the target.",
    substitute: "Creates a Substitute.",
    protect: "Protects the user.",
    endure: "The user survives with at least 1 HP.",
    ingrain: "Roots the user in place.",
    aquaring: "Surrounds the user with Aqua Ring.",
  },
};

function secondaryEffectLines(rawEffect: unknown, language: Language): string[] {
  const effect = asRecord(rawEffect);
  const chance = typeof effect.chance === "number" ? effect.chance : null;
  const lines: string[] = [];
  if (typeof effect.status === "string") {
    const line = formatStatus(effect.status, chance, language);
    if (line) lines.push(line);
  }
  if (typeof effect.volatile_status === "string") {
    if (effect.volatile_status === "flinch") {
      lines.push(chance === null
        ? (language === "de" ? "Lässt das Ziel zurückschrecken." : "Makes the target flinch.")
        : (language === "de"
          ? `${chance}% Chance, das Ziel zurückschrecken zu lassen.`
          : `${chance}% chance to make the target flinch.`));
    } else if (effect.volatile_status === "confusion") {
      lines.push(chance === null
        ? VOLATILE_TEXT[language].confusion
        : (language === "de"
          ? `${chance}% Chance, das Ziel zu verwirren.`
          : `${chance}% chance to confuse the target.`));
    }
  }
  for (const line of formatStatChanges(effect.stat_changes, "target", language)) {
    lines.push(chance === null ? line : `${chance}% ${language === "de" ? "Chance" : "chance"}: ${line}`);
  }
  for (const line of formatStatChanges(effect.self_stat_changes, "user", language)) {
    lines.push(chance === null ? line : `${chance}% ${language === "de" ? "Chance" : "chance"}: ${line}`);
  }
  return lines;
}

export function formatMoveEffect(move: Move, language: Language): string {
  const effects = asRecord(move.effects);
  let lines: string[] = [];
  let mechanicLines = 0;
  const add = (line: string | null | undefined, mechanic = true) => {
    const clean = line?.replace(/\s+/g, " ").trim();
    if (!clean || lines.includes(clean)) return;
    lines.push(clean);
    if (mechanic) mechanicLines += 1;
  };

  if (move.priority !== 0) {
    add(language === "de" ? `Priorität: ${move.priority > 0 ? "+" : ""}${move.priority}` : `Priority: ${move.priority > 0 ? "+" : ""}${move.priority}`);
  }
  if (move.is_spread_move) {
    if (language === "de") {
      add(move.target === "allAdjacent" ? "Trifft alle angrenzenden Pokémon." : move.target === "allAdjacentFoes" ? "Trifft beide Gegner." : "Mehrziel-Attacke.", false);
    } else {
      add(move.target === "allAdjacent" ? "Hits all adjacent Pokémon." : move.target === "allAdjacentFoes" ? "Hits all adjacent foes." : "Spread move.", false);
    }
  }

  if (typeof effects.status === "string") add(formatStatus(effects.status, null, language));
  if (typeof effects.volatile_status === "string") add(VOLATILE_TEXT[language][effects.volatile_status]);
  const statSubject = move.target === "self" ? "user" : move.target === "allAdjacentFoes" ? "foes" : "target";
  formatStatChanges(effects.stat_changes, statSubject, language).forEach((line) => add(line));
  formatStatChanges(effects.self_stat_changes, "user", language).forEach((line) => add(line));
  if (Array.isArray(effects.secondary_effects)) {
    effects.secondary_effects.forEach((effect) => secondaryEffectLines(effect, language).forEach((line) => add(line)));
  }

  const drain = fractionPercent(effects.drain);
  if (drain) add(language === "de" ? `Heilt den Anwender um ${drain} des verursachten Schadens.` : `Restores the user's HP by ${drain} of the damage dealt.`);
  const recoil = fractionPercent(effects.recoil);
  if (recoil) add(language === "de" ? `Rückstoß: ${recoil} des verursachten Schadens.` : `Recoil: ${recoil} of the damage dealt.`);
  const healing = fractionPercent(effects.healing);
  if (healing) add(language === "de" ? `Heilt ${healing} der maximalen KP des Anwenders.` : `Heals ${healing} of the user's maximum HP.`);

  if (typeof effects.multi_hit === "number") {
    add(language === "de" ? `Trifft ${effects.multi_hit}-mal.` : `Hits ${effects.multi_hit} times.`);
  } else if (Array.isArray(effects.multi_hit) && effects.multi_hit.length === 2) {
    add(language === "de" ? `Trifft ${effects.multi_hit[0]}–${effects.multi_hit[1]}-mal.` : `Hits ${effects.multi_hit[0]}–${effects.multi_hit[1]} times.`);
  }
  if (effects.fixed_damage === "level") add(language === "de" ? "Verursacht Schaden in Höhe des Levels des Anwenders." : "Deals damage equal to the user's level.");
  if (effects.one_hit_ko) add(language === "de" ? "K.O.-Treffer mit einem Treffer." : "One-hit KO move.");
  if (effects.always_critical) {
    add(language === "de" ? "Landet immer einen Volltreffer." : "Always results in a critical hit.");
  } else if (typeof effects.critical_hit_ratio === "number" && effects.critical_hit_ratio > 1) {
    add(language === "de" ? `Volltrefferquote: +${effects.critical_hit_ratio - 1} Stufe.` : `Critical-hit ratio: +${effects.critical_hit_ratio - 1} stage.`);
  }
  if (effects.self_switch) add(language === "de" ? "Der Anwender wechselt nach der Attacke aus." : "The user switches out after the move.");
  if (effects.force_switch) add(language === "de" ? "Zwingt das Ziel zum Wechsel." : "Forces the target to switch.");
  if (effects.self_destruct === "always") add(language === "de" ? "Der Anwender wird nach dem Einsatz kampfunfähig." : "The user faints after use.");
  if (effects.self_destruct === "ifHit") add(language === "de" ? "Der Anwender wird kampfunfähig, wenn die Attacke trifft." : "The user faints if the move hits.");
  if (effects.breaks_protect) add(language === "de" ? "Durchbricht Schutz-Attacken." : "Breaks through Protect-like effects.");
  if (effects.ignores_ability) add(language === "de" ? "Ignoriert die Fähigkeit des Ziels." : "Ignores the target's Ability.");
  if (effects.ignores_defense) add(language === "de" ? "Ignoriert die Verteidigung des Ziels." : "Ignores the target's Defense.");
  if (effects.ignores_evasion) add(language === "de" ? "Ignoriert Ausweichwert-Modifikatoren." : "Ignores evasion modifiers.");
  if (effects.thaws_target) add(language === "de" ? "Taut ein eingefrorenes Ziel auf." : "Thaws a frozen target.");

  const weatherNames: Record<Language, Record<string, string>> = {
    de: { RainDance: "Regen", Sandstorm: "Sandsturm", hail: "Hagel", snowscape: "Schnee", sunnyday: "Sonne" },
    en: { RainDance: "rain", Sandstorm: "sandstorm", hail: "hail", snowscape: "snow", sunnyday: "sunlight" },
  };
  if (typeof effects.weather === "string") {
    const weather = weatherNames[language][effects.weather] ?? effects.weather;
    add(language === "de" ? `Setzt das Wetter auf ${weather}.` : `Sets ${weather}.`);
  }
  const terrainNames: Record<Language, Record<string, string>> = {
    de: { electricterrain: "Elektrofeld", grassyterrain: "Grasfeld", mistyterrain: "Nebelfeld", psychicterrain: "Psychofeld" },
    en: { electricterrain: "Electric Terrain", grassyterrain: "Grassy Terrain", mistyterrain: "Misty Terrain", psychicterrain: "Psychic Terrain" },
  };
  if (typeof effects.terrain === "string") {
    const terrain = terrainNames[language][effects.terrain] ?? effects.terrain;
    add(language === "de" ? `Erzeugt ${terrain}.` : `Sets ${terrain}.`);
  }

  const rawSummary = language === "de"
    ? (effects.summary_de || effects.summary_en)
    : effects.summary_en;
  const summary = typeof rawSummary === "string" ? rawSummary.trim() : "";
  const usefulSummary = summary && summary !== "No additional effect." && summary !== "Kein zusätzlicher Effekt.";
  const fallbackPrefix = language === "de" && (effects.summary_de_is_fallback || !effects.summary_de)
    ? "Details (EN): "
    : "";

  if (effects.has_custom_logic && usefulSummary) {
    const prefix = language === "de" ? "Priorität: " : "Priority: ";
    lines = lines.filter((line) => line.startsWith(prefix));
    mechanicLines = lines.length;
    add(`${fallbackPrefix}${summary}`, false);
  } else if (mechanicLines === 0 && usefulSummary) {
    add(`${fallbackPrefix}${summary}`, false);
  }

  return lines.join("\n") || (language === "de" ? "Kein zusätzlicher Effekt." : "No additional effect.");
}

export function groupAndSortMoves(
  moves: Move[],
  language: Language,
): Array<{ type: string; moves: Move[] }> {
  const grouped = new Map<string, Map<MoveCategory, Move[]>>();
  for (const move of moves) {
    const byCategory = grouped.get(move.type) ?? new Map<MoveCategory, Move[]>();
    const categoryMoves = byCategory.get(move.category) ?? [];
    categoryMoves.push(move);
    byCategory.set(move.category, categoryMoves);
    grouped.set(move.type, byCategory);
  }

  const known = TYPE_ORDER.filter((type) => grouped.has(type));
  const unknown = [...grouped.keys()]
    .filter((type) => !TYPE_ORDER.includes(type as (typeof TYPE_ORDER)[number]))
    .sort();

  return [...known, ...unknown].map((type) => {
    const byCategory = grouped.get(type)!;
    const sorted: Move[] = [];
    for (const category of ["physical", "special", "status"] as MoveCategory[]) {
      const categoryMoves = byCategory.get(category);
      if (!categoryMoves) continue;
      sorted.push(...categoryMoves.toSorted((left, right) => {
        const powerDifference = (right.power ?? -1) - (left.power ?? -1);
        if (powerDifference !== 0) return powerDifference;
        return localizedName(left, language).localeCompare(
          localizedName(right, language),
          language,
          { sensitivity: "base" },
        );
      }));
    }
    return { type, moves: sorted };
  });
}

export async function loadPokedexBundle(signal?: AbortSignal): Promise<PokedexBundle> {
  const files = [
    "pokemon_v2",
    "moves",
    "learnsets",
    "abilities",
    "regulations",
  ] as const;
  const responses = await Promise.all(files.map((name) => fetch(
    publicPath(`data/${name}.json`),
    { signal },
  )));
  for (const response of responses) {
    if (!response.ok) {
      throw new Error(`Pokédex-Daten konnten nicht geladen werden (${response.status}).`);
    }
  }
  const [pokemon, moves, learnsets, abilities, regulations] = await Promise.all(
    responses.map((response) => response.json()),
  );
  return {
    pokemon: pokemon as PokemonSpecies[],
    moves: moves as Move[],
    learnsets: learnsets as Learnset[],
    abilities: abilities as AbilityRecord[],
    regulations: regulations as RegulationsData,
  };
}

export class PokedexIndex {
  readonly forms: PokemonForm[];
  readonly moves: Move[];
  readonly currentRegulationId: string;
  readonly movesById = new Map<number, Move>();
  readonly formsByPokemonId = new Map<number, PokemonForm>();
  readonly formsByApiName = new Map<string, PokemonForm>();
  readonly learnsetsByPokemonId = new Map<number, Learnset>();
  readonly abilitiesByApiName = new Map<string, AbilityRecord>();
  readonly regulationsById = new Map<string, Regulation>();
  private readonly regulationOrder: Regulation[];
  private readonly formsBySpeciesId = new Map<number, PokemonForm[]>();
  private readonly defaultFormBySpeciesId = new Map<number, PokemonForm>();
  private readonly resolvedMoveIdsCache = new Map<number, Set<number>>();

  constructor(bundle: PokedexBundle) {
    this.moves = bundle.moves;
    this.currentRegulationId = bundle.regulations.current_regulation_id;
    this.regulationOrder = bundle.regulations.regulations;
    this.forms = bundle.pokemon.flatMap((species) => species.forms.map((form) => ({
      ...form,
      national_dex: species.dex,
      evolves_from_species_id: species.evolves_from_species_id,
    }))).toSorted((left, right) => (
      left.national_dex - right.national_dex
      || left.pokemon_id - right.pokemon_id
    ));

    for (const move of bundle.moves) this.movesById.set(move.move_id, move);
    for (const learnset of bundle.learnsets) {
      this.learnsetsByPokemonId.set(learnset.pokemon_id, learnset);
    }
    for (const ability of bundle.abilities) {
      this.abilitiesByApiName.set(ability.api_name, ability);
    }
    for (const regulation of this.regulationOrder) {
      this.regulationsById.set(regulation.id, regulation);
    }
    for (const form of this.forms) {
      this.formsByPokemonId.set(form.pokemon_id, form);
      this.formsByApiName.set(form.api_name, form);
      const speciesForms = this.formsBySpeciesId.get(form.national_dex) ?? [];
      speciesForms.push(form);
      this.formsBySpeciesId.set(form.national_dex, speciesForms);
      if (form.is_default) this.defaultFormBySpeciesId.set(form.national_dex, form);
    }
    for (const [speciesId, speciesForms] of this.formsBySpeciesId) {
      if (!this.defaultFormBySpeciesId.has(speciesId)) {
        this.defaultFormBySpeciesId.set(
          speciesId,
          speciesForms.toSorted((a, b) => a.pokemon_id - b.pokemon_id)[0],
        );
      }
    }
  }

  regulationChoices(): Array<Pick<Regulation, "id" | "name" | "status">> {
    const current = this.regulationsById.get(this.currentRegulationId);
    const choices: Array<Pick<Regulation, "id" | "name" | "status">> = [];
    if (current) choices.push(current);
    choices.push({ id: "national_dex", name: "National Dex", status: "all" });
    choices.push(...this.regulationOrder.filter((item) => item.id !== this.currentRegulationId));
    return choices;
  }

  formsForRegulation(regulationId: string): PokemonForm[] {
    if (regulationId === "national_dex") return this.forms;
    const regulation = this.regulationsById.get(regulationId);
    if (!regulation) return [];
    const allowed = new Set(regulation.pokemon_ids);
    return this.forms.filter((form) => allowed.has(form.pokemon_id));
  }

  formInRegulation(form: PokemonForm, regulationId: string): boolean {
    if (regulationId === "national_dex") return true;
    return this.regulationsById.get(regulationId)?.pokemon_ids.includes(form.pokemon_id) ?? false;
  }

  abilityFor(reference: PokemonAbility): AbilityRecord | PokemonAbility {
    return this.abilitiesByApiName.get(reference.api_name) ?? reference;
  }

  resolvedMoveIds(pokemonId: number): Set<number> {
    return new Set(this.collectResolvedMoveIds(pokemonId, new Set()));
  }

  resolvedMoves(pokemonId: number): Move[] {
    return [...this.resolvedMoveIds(pokemonId)]
      .toSorted((a, b) => a - b)
      .map((id) => this.movesById.get(id))
      .filter((move): move is Move => move !== undefined);
  }

  scopeEntities(forms: PokemonForm[]): ScopeEntities {
    const entities: ScopeEntities = {
      types: new Set(),
      abilities: new Set(),
      moves: new Set(),
    };
    for (const form of forms) {
      form.types.forEach((type) => entities.types.add(type));
      form.abilities.forEach((ability) => entities.abilities.add(ability.api_name));
      this.resolvedMoveIds(form.pokemon_id).forEach((id) => entities.moves.add(id));
    }
    return entities;
  }

  formMatchesFilters(form: PokemonForm, filters: ActiveFilter[]): boolean {
    return filters.every((filter) => {
      if (filter.kind === "type") return form.types.includes(String(filter.value));
      if (filter.kind === "ability") {
        return form.abilities.some((ability) => ability.api_name === String(filter.value));
      }
      return this.resolvedMoveIds(form.pokemon_id).has(Number(filter.value));
    });
  }

  private collectResolvedMoveIds(pokemonId: number, visiting: Set<number>): Set<number> {
    const cached = this.resolvedMoveIdsCache.get(pokemonId);
    if (cached) return cached;
    if (visiting.has(pokemonId)) return new Set();

    const learnset = this.learnsetsByPokemonId.get(pokemonId);
    const moveIds = new Set(learnset?.move_ids ?? []);
    const form = this.formsByPokemonId.get(pokemonId);
    const parent = form ? this.selectParentForm(form) : undefined;
    if (parent) {
      visiting.add(pokemonId);
      this.collectResolvedMoveIds(parent.pokemon_id, visiting).forEach((id) => moveIds.add(id));
      visiting.delete(pokemonId);
    }
    this.resolvedMoveIdsCache.set(pokemonId, moveIds);
    return moveIds;
  }

  private selectParentForm(form: PokemonForm): PokemonForm | undefined {
    const override = PARENT_FORM_OVERRIDES[form.api_name];
    if (override && this.formsByApiName.has(override)) return this.formsByApiName.get(override);
    if (form.evolves_from_species_id === null) return undefined;
    const candidates = this.formsBySpeciesId.get(form.evolves_from_species_id) ?? [];
    if (candidates.length === 0) return undefined;

    const parts = new Set(form.api_name.split("-"));
    const regionalToken = REGIONAL_TOKENS.find((token) => parts.has(token));
    if (regionalToken) {
      const regionalCandidates = candidates.filter((candidate) => (
        candidate.api_name.split("-").includes(regionalToken)
      ));
      if (regionalCandidates.length > 0) {
        return regionalCandidates.toSorted((left, right) => (
          Number(right.is_default) - Number(left.is_default)
          || left.pokemon_id - right.pokemon_id
        ))[0];
      }
    }
    return this.defaultFormBySpeciesId.get(form.evolves_from_species_id);
  }
}
