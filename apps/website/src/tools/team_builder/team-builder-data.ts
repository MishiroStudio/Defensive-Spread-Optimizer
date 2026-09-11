import { NATURES } from "../../shared/calculations/natures";
import {
  CATEGORY_ICON_FILES,
  MAX_STAT_POINTS,
  MAX_TOTAL_STAT_POINTS,
  PokedexIndex,
  STAT_ORDER,
  TYPE_NAMES,
  TYPE_ORDER,
  calculateAllStats,
  formatMoveEffect,
  localizedName,
  moveDisplayPp,
  moveMatchesRubric,
  normalize,
  type BaseStats,
  type Language,
  type Move,
  type MoveCategory,
  type MoveRubric,
  type PokedexBundle,
  type PokemonForm,
  type PokemonSpecies,
  type Regulation,
  type StatKey,
} from "../pokedex/pokedex-data";
import { publicPath } from "../pokedex/public-path";

export type { Language, Move, MoveCategory, MoveRubric, PokemonForm, StatKey };

export type ItemCategory =
  | "all"
  | "stat-boost"
  | "power-boost"
  | "defense"
  | "healing"
  | "effect-duration"
  | "berries"
  | "mega-stones"
  | "other";

export interface Item {
  item_id: number;
  api_name: string;
  showdown_id?: string;
  name_en: string;
  name_de: string;
  description_en?: string;
  description_de?: string;
  category?: string;
  restricted_to?: string[];
  mega_stone?: Record<string, string>;
  legal_in_regulations?: string[];
  effect_categories?: string[];
  mechanics?: { tags?: string[]; [key: string]: unknown };
}

export type StatPoints = Record<StatKey, number>;

export interface TeamMember {
  pokemon_id: number;
  pokemon_api_name: string;
  ability_id: string | null;
  item_id: string | null;
  move_ids: string[];
  stat_points: StatPoints;
  nature_increased: StatKey | null;
  nature_decreased: StatKey | null;
  /** Editor-only memory. It is deliberately not persisted. */
  ability_ids_by_form?: Record<number, string>;
}

export interface TeamSnapshot {
  id?: string;
  name: string;
  regulation_id: string;
  active_slots: Array<TeamMember | null>;
  bench: TeamMember[];
}

export interface TeamFolder {
  id: string;
  name: string;
  teams: TeamSnapshot[];
}

export interface TeamLibraryDocument {
  schema_version: 1;
  folders: TeamFolder[];
}

export interface TeamBuilderBundle extends PokedexBundle {
  items: Item[];
}

export const EMPTY_STAT_POINTS = (): StatPoints => ({
  hp: 0,
  atk: 0,
  def: 0,
  spa: 0,
  spd: 0,
  spe: 0,
});

export const ITEM_CATEGORIES: ItemCategory[] = [
  "all",
  "stat-boost",
  "power-boost",
  "defense",
  "healing",
  "effect-duration",
  "berries",
  "mega-stones",
  "other",
];

export const ITEM_CATEGORY_NAMES: Record<Language, Record<ItemCategory, string>> = {
  de: {
    all: "Alle",
    "stat-boost": "Statuswerte ↑",
    "power-boost": "Stärke ↑",
    defense: "Verteidigung",
    healing: "Heilung",
    "effect-duration": "Effektlänge",
    berries: "Beeren",
    "mega-stones": "Mega-Steine",
    other: "Andere",
  },
  en: {
    all: "All",
    "stat-boost": "Stats ↑",
    "power-boost": "Power ↑",
    defense: "Defense",
    healing: "Recovery",
    "effect-duration": "Effect duration",
    berries: "Berries",
    "mega-stones": "Mega Stones",
    other: "Other",
  },
};

const FORM_NAME_OVERRIDES: Record<string, string> = {
  "calyrex-ice": "Calyrex-Ice",
  "calyrex-shadow": "Calyrex-Shadow",
  "darmanitan-galar-standard": "Darmanitan-Galar",
  "darmanitan-galar-zen": "Darmanitan-Galar-Zen",
  "indeedee-female": "Indeedee-F",
  "meowstic-female": "Meowstic-F",
  "ogerpon-wellspring-mask": "Ogerpon-Wellspring",
  "ogerpon-hearthflame-mask": "Ogerpon-Hearthflame",
  "ogerpon-cornerstone-mask": "Ogerpon-Cornerstone",
  "urshifu-rapid-strike": "Urshifu-Rapid-Strike",
  "nidoran-f": "Nidoran-F",
  "nidoran-m": "Nidoran-M",
  flabebe: "Flabebe",
  "basculin-red-striped": "Basculin-Red-Striped",
  "basculegion-female": "Basculegion-F",
  "oinkologne-female": "Oinkologne-F",
  "pyroar-female": "Pyroar-F",
};

const NATURE_STAT_KEYS: Record<Exclude<StatKey, "hp">, string> = {
  atk: "attack",
  def: "defense",
  spa: "special_attack",
  spd: "special_defense",
  spe: "speed",
};

function showdownId(value: unknown): string {
  return String(value ?? "").toLocaleLowerCase().replace(/[^a-z0-9]/g, "");
}

function lookupKeys(value: unknown): string[] {
  const text = String(value ?? "").trim();
  return text ? [...new Set([normalize(text), showdownId(text)])] : [];
}

function cloneMember(member: TeamMember): TeamMember {
  return {
    ...member,
    move_ids: [...member.move_ids],
    stat_points: { ...member.stat_points },
    ability_ids_by_form: { ...(member.ability_ids_by_form ?? {}) },
  };
}

export function normalizeMember(value: unknown): TeamMember | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const raw = value as Partial<TeamMember>;
  if (!Number.isFinite(Number(raw.pokemon_id)) || !raw.pokemon_api_name) return null;
  const points = EMPTY_STAT_POINTS();
  for (const stat of STAT_ORDER) {
    const requested = Number(raw.stat_points?.[stat] ?? 0);
    points[stat] = Math.max(0, Math.min(MAX_STAT_POINTS, Math.trunc(requested || 0)));
  }
  let overflow = Math.max(0, Object.values(points).reduce((sum, point) => sum + point, 0) - MAX_TOTAL_STAT_POINTS);
  for (const stat of [...STAT_ORDER].reverse()) {
    const reduction = Math.min(points[stat], overflow);
    points[stat] -= reduction;
    overflow -= reduction;
  }
  const natureStat = (stat: unknown): StatKey | null => (
    stat === "atk" || stat === "def" || stat === "spa" || stat === "spd" || stat === "spe"
      ? stat
      : null
  );
  const abilityIdsByForm: Record<number, string> = {};
  if (raw.ability_ids_by_form && typeof raw.ability_ids_by_form === "object") {
    Object.entries(raw.ability_ids_by_form).forEach(([pokemonId, abilityId]) => {
      const numericId = Number(pokemonId);
      if (Number.isInteger(numericId) && numericId > 0 && typeof abilityId === "string" && abilityId) {
        abilityIdsByForm[numericId] = abilityId;
      }
    });
  }
  if (raw.ability_id) abilityIdsByForm[Math.trunc(Number(raw.pokemon_id))] = String(raw.ability_id);
  return {
    pokemon_id: Math.trunc(Number(raw.pokemon_id)),
    pokemon_api_name: String(raw.pokemon_api_name),
    ability_id: raw.ability_id ? String(raw.ability_id) : null,
    item_id: raw.item_id ? String(raw.item_id) : null,
    move_ids: Array.isArray(raw.move_ids)
      ? raw.move_ids.filter(Boolean).map(String).slice(0, 4)
      : [],
    stat_points: points,
    nature_increased: natureStat(raw.nature_increased),
    nature_decreased: natureStat(raw.nature_decreased),
    ability_ids_by_form: abilityIdsByForm,
  };
}

export function persistedMember(member: TeamMember | null): TeamMember | null {
  if (!member) return null;
  const copy = cloneMember(member);
  delete copy.ability_ids_by_form;
  return copy;
}

export async function loadTeamBuilderBundle(signal?: AbortSignal): Promise<TeamBuilderBundle> {
  const files = ["pokemon_v2", "moves", "learnsets", "abilities", "regulations", "items"] as const;
  const responses = await Promise.all(files.map((name) => fetch(
    publicPath(`data/${name}.json`),
    { signal },
  )));
  for (const response of responses) {
    if (!response.ok) throw new Error(`Team-Builder-Daten konnten nicht geladen werden (${response.status}).`);
  }
  const [pokemon, moves, learnsets, abilities, regulations, items] = await Promise.all(
    responses.map((response) => response.json()),
  );
  return {
    pokemon: pokemon as PokemonSpecies[],
    moves: moves as Move[],
    learnsets: learnsets as TeamBuilderBundle["learnsets"],
    abilities: abilities as TeamBuilderBundle["abilities"],
    regulations: regulations as TeamBuilderBundle["regulations"],
    items: items as Item[],
  };
}

export class TeamBuilderData {
  readonly pokedex: PokedexIndex;
  readonly species: PokemonSpecies[];
  readonly items: Item[];
  readonly itemsByName = new Map<string, Item>();
  readonly movesByName = new Map<string, Move>();
  readonly formsBySpecies = new Map<number, PokemonForm[]>();
  readonly speciesByDex = new Map<number, PokemonSpecies>();
  readonly currentRegulationId: string;
  private readonly formSearchTokens = new Map<number, Set<string>>();
  private readonly maximumStatsCache = new Map<string, BaseStats>();
  private readonly pasteForms = new Map<string, PokemonForm[]>();
  private readonly pasteItems = new Map<string, string>();
  private readonly pasteMoves = new Map<string, string>();

  constructor(bundle: TeamBuilderBundle) {
    this.pokedex = new PokedexIndex(bundle);
    this.species = bundle.pokemon;
    this.items = bundle.items;
    this.currentRegulationId = this.pokedex.currentRegulationId;
    bundle.pokemon.forEach((species) => this.speciesByDex.set(species.dex, species));
    this.pokedex.forms.forEach((form) => {
      const forms = this.formsBySpecies.get(form.national_dex) ?? [];
      forms.push(form);
      this.formsBySpecies.set(form.national_dex, forms);
    });
    bundle.items.forEach((item) => this.itemsByName.set(item.api_name, item));
    bundle.moves.forEach((move) => this.movesByName.set(move.api_name, move));
    this.buildPasteLookups();
  }

  newMember(form: PokemonForm): TeamMember {
    const ability = form.abilities.length === 1 ? form.abilities[0].api_name : null;
    const member: TeamMember = {
      pokemon_id: form.pokemon_id,
      pokemon_api_name: form.api_name,
      ability_id: ability,
      item_id: null,
      move_ids: [],
      stat_points: EMPTY_STAT_POINTS(),
      nature_increased: null,
      nature_decreased: null,
      ability_ids_by_form: ability ? { [form.pokemon_id]: ability } : {},
    };
    return member;
  }

  form(member: TeamMember): PokemonForm {
    const found = this.pokedex.formsByPokemonId.get(member.pokemon_id)
      ?? this.pokedex.formsByApiName.get(member.pokemon_api_name);
    if (!found) throw new Error(`Unbekannte Pokémon-Form: ${member.pokemon_api_name}`);
    return found;
  }

  compactDisplayForm(member: TeamMember): PokemonForm {
    const current = this.form(member);
    if (!/-mega(?:-|$)/.test(current.api_name)) return current;
    return this.formsBySpecies.get(current.national_dex)?.find((form) => form.is_default) ?? current;
  }

  relatedForms(member: TeamMember, regulationId: string): PokemonForm[] {
    const current = this.form(member);
    const forms = (this.formsBySpecies.get(current.national_dex) ?? [])
      .filter((form) => this.pokedex.formInRegulation(form, regulationId));
    if (!forms.some((form) => form.pokemon_id === current.pokemon_id)) forms.push(current);
    return forms.toSorted((a, b) => Number(b.is_default) - Number(a.is_default) || a.pokemon_id - b.pokemon_id);
  }

  regulationChoices(): Regulation[] {
    const current = this.pokedex.regulationsById.get(this.currentRegulationId);
    const past = [...this.pokedex.regulationsById.values()]
      .filter((item) => item.id !== this.currentRegulationId)
      .toSorted((a, b) => (b.year ?? 0) - (a.year ?? 0) || (b.code ?? b.id).localeCompare(a.code ?? a.id));
    return [
      ...(current ? [current] : []),
      { id: "national_dex", name: "National Dex", status: "all", pokemon_ids: [] },
      ...past,
    ];
  }

  regulationFormatName(regulationId: string): string {
    if (regulationId === "national_dex") return "National Dex";
    const regulation = this.pokedex.regulationsById.get(regulationId);
    return regulation?.format_name ?? regulation?.name ?? "Champions";
  }

  formsForRegulation(regulationId: string): PokemonForm[] {
    return this.pokedex.formsForRegulation(regulationId);
  }

  searchForms(query: string, regulationId: string, limit = 40): PokemonForm[] {
    const clean = query.trim();
    if (!clean) return [];
    const forms = this.formsForRegulation(regulationId);
    if (/^\d+$/.test(clean)) {
      return forms.filter((form) => form.national_dex === Number(clean)).slice(0, limit);
    }
    const needle = normalize(clean);
    return forms.flatMap((form): Array<[number, number, number, PokemonForm]> => {
      const names = [form.api_name, form.name_de, form.name_en].map(normalize);
      const tokens = this.searchTokensForForm(form);
      let rank: number | null = null;
      if (names.includes(needle)) rank = 0;
      else if (names.some((name) => name.startsWith(needle))) rank = 1;
      else if (names.some((name) => name.includes(needle))) rank = 2;
      else if (tokens.has(needle)) rank = 3;
      else if ([...tokens].some((token) => token.startsWith(needle))) rank = 4;
      else if ([...tokens].some((token) => token.includes(needle))) rank = 5;
      return rank === null ? [] : [[rank, form.national_dex, form.pokemon_id, form]];
    }).toSorted((a, b) => a[0] - b[0] || a[1] - b[1] || a[2] - b[2]).slice(0, limit).map((entry) => entry[3]);
  }

  resolvedMoves(member: TeamMember): Move[] {
    return this.pokedex.resolvedMoves(member.pokemon_id);
  }

  sortedMoves(member: TeamMember, language: Language): Move[] {
    const typeRank = new Map<string, number>(TYPE_ORDER.map((type, index) => [type, index]));
    const categoryRank: Record<MoveCategory, number> = { physical: 0, special: 1, status: 2 };
    return this.resolvedMoves(member).toSorted((a, b) => (
      (typeRank.get(a.type) ?? TYPE_ORDER.length) - (typeRank.get(b.type) ?? TYPE_ORDER.length)
      || categoryRank[a.category] - categoryRank[b.category]
      || (b.power ?? -1) - (a.power ?? -1)
      || localizedName(a, language).localeCompare(localizedName(b, language), language)
    ));
  }

  filteredMoves(
    member: TeamMember,
    language: Language,
    category: MoveCategory | "",
    rubric: MoveRubric | "",
    query = "",
  ): Move[] {
    const needle = normalize(query);
    return this.sortedMoves(member, language).filter((move) => (
      (!category || move.category === category)
      && moveMatchesRubric(move, rubric)
      && (!needle || [move.api_name, move.name_de, move.name_en].some((name) => normalize(name).includes(needle)))
    ));
  }

  moveDescription(moveId: string, language: Language): string {
    const move = this.movesByName.get(moveId);
    return move ? formatMoveEffect(move, language) : "–";
  }

  movePp(member: TeamMember, move: Move): string {
    const source = this.pokedex.learnsetsByPokemonId.get(member.pokemon_id)?.learnset_source;
    return moveDisplayPp(move, source);
  }

  legalItems(regulationId: string, language: Language): Item[] {
    const values = regulationId === "national_dex"
      ? this.items
      : this.items.filter((item) => item.legal_in_regulations?.includes(regulationId));
    return values.toSorted((a, b) => localizedName(a, language).localeCompare(localizedName(b, language), language));
  }

  availableItems(
    member: TeamMember,
    regulationId: string,
    language: Language,
    category: ItemCategory,
    query = "",
  ): Item[] {
    const needle = normalize(query);
    return this.legalItems(regulationId, language).filter((item) => (
      this.megaStoneMatches(item, member)
      && this.itemMatchesCategory(item, category)
      && (!needle || [item.api_name, item.name_de, item.name_en].some((name) => normalize(name).includes(needle)))
    ));
  }

  itemDescription(itemId: string, language: Language): string {
    const item = this.itemsByName.get(itemId);
    return String(item?.[`description_${language}`] ?? item?.description_en ?? "–");
  }

  isMegaStone(item: Item): boolean {
    return item.category === "mega-stones"
      || item.mechanics?.tags?.includes("mega-evolution") === true
      || Object.keys(item.mega_stone ?? {}).length > 0;
  }

  megaStoneMatches(item: Item, member: TeamMember): boolean {
    if (!this.isMegaStone(item)) return true;
    const form = this.form(member);
    const selectedName = form.api_name;
    const selectedId = showdownId(selectedName);
    const megaMap = item.mega_stone ?? {};
    const targets = Object.values(megaMap).map(showdownId);
    if (/-mega(?:-|$)/.test(selectedName) || targets.includes(selectedId)) return targets.includes(selectedId);
    const owners = [...(item.restricted_to ?? []), ...Object.keys(megaMap)].map(showdownId);
    return owners.includes(selectedId) || targets.some((target) => target.startsWith(`${selectedId}mega`));
  }

  megaStoneForSelectedForm(member: TeamMember, regulationId: string): Item | null {
    const selectedId = showdownId(this.form(member).api_name);
    return this.legalItems(regulationId, "en").find((item) => (
      this.isMegaStone(item)
      && Object.values(item.mega_stone ?? {}).map(showdownId).includes(selectedId)
    )) ?? null;
  }

  abilityDescription(abilityId: string, language: Language): string {
    const ability = this.pokedex.abilitiesByApiName.get(abilityId);
    return String(ability?.[`description_${language}`] ?? ability?.description_en ?? "–");
  }

  calculatedStats(member: TeamMember, withPoints = true): BaseStats {
    const natures = Object.fromEntries(STAT_ORDER.map((stat) => [stat, 1])) as Record<StatKey, number>;
    if (member.nature_increased) natures[member.nature_increased] = 1.1;
    if (member.nature_decreased) natures[member.nature_decreased] = 0.9;
    return calculateAllStats(
      this.form(member).base_stats,
      withPoints ? member.stat_points : EMPTY_STAT_POINTS(),
      natures,
    );
  }

  maximumStats(regulationId: string): BaseStats {
    const cached = this.maximumStatsCache.get(regulationId);
    if (cached) return cached;
    const maximum = { hp: 1, atk: 1, def: 1, spa: 1, spd: 1, spe: 1 };
    const points = Object.fromEntries(STAT_ORDER.map((stat) => [stat, MAX_STAT_POINTS])) as StatPoints;
    for (const form of this.formsForRegulation(regulationId)) {
      const natures = Object.fromEntries(STAT_ORDER.map((stat) => [stat, stat === "hp" ? 1 : 1.1])) as Record<StatKey, number>;
      const stats = calculateAllStats(form.base_stats, points, natures);
      STAT_ORDER.forEach((stat) => { maximum[stat] = Math.max(maximum[stat], stats[stat]); });
    }
    this.maximumStatsCache.set(regulationId, maximum);
    return maximum;
  }

  natureName(member: TeamMember, language: Language): string {
    const positive = member.nature_increased ? NATURE_STAT_KEYS[member.nature_increased as Exclude<StatKey, "hp">] : null;
    const negative = member.nature_decreased ? NATURE_STAT_KEYS[member.nature_decreased as Exclude<StatKey, "hp">] : null;
    if (!positive && !negative) return language === "de" ? "Ernst" : "Serious";
    if (!positive) return language === "de" ? "+ wählen" : "Choose +";
    if (!negative) return language === "de" ? "− wählen" : "Choose −";
    const nature = Object.values(NATURES).find((entry) => entry.positive === positive && entry.negative === negative);
    return nature ? (language === "de" ? nature.name_de : nature.name_en) : (language === "de" ? "Ernst" : "Serious");
  }

  natureSummary(member: TeamMember, language: Language, labels: Record<StatKey, string>): string {
    const name = this.natureName(member, language);
    if (!member.nature_increased || !member.nature_decreased) return name;
    return `${name} (${labels[member.nature_increased]}+ / ${labels[member.nature_decreased]}−)`;
  }

  switchForm(member: TeamMember, pokemonId: number, regulationId: string): TeamMember {
    const nextForm = this.pokedex.formsByPokemonId.get(pokemonId);
    const currentForm = this.form(member);
    if (!nextForm || nextForm.national_dex !== currentForm.national_dex) return cloneMember(member);
    const next = cloneMember(member);
    if (next.ability_id) next.ability_ids_by_form![currentForm.pokemon_id] = next.ability_id;
    const previousAbility = next.ability_id;
    next.pokemon_id = nextForm.pokemon_id;
    next.pokemon_api_name = nextForm.api_name;
    const validAbilities = new Set(nextForm.abilities.map((ability) => ability.api_name));
    const remembered = next.ability_ids_by_form?.[nextForm.pokemon_id];
    next.ability_id = remembered && validAbilities.has(remembered)
      ? remembered
      : previousAbility && validAbilities.has(previousAbility) ? previousAbility : null;
    if (!next.ability_id && nextForm.abilities.length === 1) next.ability_id = nextForm.abilities[0].api_name;
    if (next.ability_id) next.ability_ids_by_form![nextForm.pokemon_id] = next.ability_id;
    const validMoves = new Set(this.pokedex.resolvedMoves(nextForm.pokemon_id).map((move) => move.api_name));
    next.move_ids = next.move_ids.filter((id) => validMoves.has(id));
    const megaStone = this.megaStoneForSelectedForm(next, regulationId);
    if (megaStone) next.item_id = megaStone.api_name;
    else if (next.item_id && !this.availableItems(next, regulationId, "en", "all").some((item) => item.api_name === next.item_id)) {
      next.item_id = null;
    }
    return next;
  }

  canonicalPasteName(form: PokemonForm): string {
    if (FORM_NAME_OVERRIDES[form.api_name]) return FORM_NAME_OVERRIDES[form.api_name];
    const species = this.speciesByDex.get(form.national_dex);
    const speciesName = species?.name_en ?? form.name_en ?? form.api_name;
    if (form.is_default) return speciesName;
    const parenthetical = form.name_en.match(/\(([^()]*)\)\s*$/)?.[1];
    let qualifier = parenthetical ?? form.api_name.replace(`${species?.api_name ?? ""}-`, "").replaceAll("-", " ").replace(/\b\w/g, (char) => char.toUpperCase());
    qualifier = ({
      Female: "F",
      Male: "M",
      "Ice Rider": "Ice",
      "Shadow Rider": "Shadow",
      "Wellspring Mask": "Wellspring",
      "Hearthflame Mask": "Hearthflame",
      "Cornerstone Mask": "Cornerstone",
    } as Record<string, string>)[qualifier] ?? qualifier;
    return `${speciesName}-${qualifier.trim().replace(/\s+/g, "-")}`;
  }

  resolvePasteForm(value: string, regulationId: string): PokemonForm | null {
    const cleaned = value.replace(/\s+\((?:M|F)\)\s*$/i, "").trim();
    const parenthetical = [...cleaned.matchAll(/\(([^()]*)\)/g)].map((match) => match[1]).reverse();
    const candidates = [cleaned, ...parenthetical.filter((item) => !["m", "f", "mega"].includes(item.toLocaleLowerCase()))];
    const allowed = new Set(this.formsForRegulation(regulationId).map((form) => form.pokemon_id));
    for (const candidate of candidates) {
      const possible = lookupKeys(candidate).flatMap((key) => this.pasteForms.get(key) ?? []);
      const unique = [...new Map(possible.map((form) => [form.pokemon_id, form])).values()];
      if (!unique.length) continue;
      const legal = unique.filter((form) => allowed.has(form.pokemon_id));
      const choices = legal.length ? legal : unique;
      return choices.find((form) => form.is_default) ?? choices[0];
    }
    return null;
  }

  resolvePasteItem(value: string): string | null {
    return lookupKeys(value).map((key) => this.pasteItems.get(key)).find(Boolean) ?? null;
  }

  resolvePasteMove(member: TeamMember, value: string): string | null {
    const resolved = lookupKeys(value).map((key) => this.pasteMoves.get(key)).find(Boolean);
    return resolved && this.resolvedMoves(member).some((move) => move.api_name === resolved) ? resolved : null;
  }

  resolvePasteAbility(member: TeamMember, value: string): string | null {
    const sought = new Set(lookupKeys(value));
    return this.form(member).abilities.find((ability) => (
      [ability.api_name, ability.name_de, ability.name_en]
        .flatMap(lookupKeys)
        .some((key) => sought.has(key))
    ))?.api_name ?? null;
  }

  resolveNature(value: string): [StatKey | null, StatKey | null] | null {
    const sought = normalize(value);
    const reverse = Object.fromEntries(Object.entries(NATURE_STAT_KEYS).map(([short, full]) => [full, short])) as Record<string, StatKey>;
    const nature = Object.values(NATURES).find((entry) => [entry.id, entry.name_en, entry.name_de].map(normalize).includes(sought));
    return nature ? [reverse[nature.positive ?? ""] ?? null, reverse[nature.negative ?? ""] ?? null] : null;
  }

  categoryIcon(move: Move): string {
    return publicPath(`assets/move-categories/${CATEGORY_ICON_FILES[move.category]}`);
  }

  private itemMatchesCategory(item: Item, category: ItemCategory): boolean {
    return category === "all"
      || (category === "mega-stones" ? this.isMegaStone(item) : item.effect_categories?.includes(category) === true);
  }

  private searchTokensForForm(form: PokemonForm): Set<string> {
    const cached = this.formSearchTokens.get(form.pokemon_id);
    if (cached) return cached;
    const values = [form.api_name, form.name_de, form.name_en];
    form.types.forEach((type) => values.push(type, TYPE_NAMES.de[type] ?? type, TYPE_NAMES.en[type] ?? type));
    form.abilities.forEach((ability) => values.push(ability.api_name, ability.name_de, ability.name_en));
    this.pokedex.resolvedMoves(form.pokemon_id).forEach((move) => values.push(move.api_name, move.name_de, move.name_en));
    const tokens = new Set(values.map(normalize).filter(Boolean));
    this.formSearchTokens.set(form.pokemon_id, tokens);
    return tokens;
  }

  private buildPasteLookups(): void {
    this.pokedex.forms.forEach((form) => {
      const species = this.speciesByDex.get(form.national_dex);
      const values = [form.api_name, form.name_en, form.name_de, this.canonicalPasteName(form)];
      if (form.is_default && species) values.push(species.api_name, species.name_en, species.name_de);
      if (form.api_name.includes("-female")) values.push(form.api_name.replace("-female", "-f"));
      if (form.api_name.includes("-male")) values.push(form.api_name.replace("-male", "-m"));
      values.flatMap(lookupKeys).forEach((key) => {
        const matches = this.pasteForms.get(key) ?? [];
        if (!matches.some((entry) => entry.pokemon_id === form.pokemon_id)) matches.push(form);
        this.pasteForms.set(key, matches);
      });
    });
    this.items.forEach((item) => {
      [item.api_name, item.showdown_id, item.name_en, item.name_de].flatMap(lookupKeys)
        .forEach((key) => this.pasteItems.set(key, item.api_name));
    });
    this.pokedex.moves.forEach((move) => {
      [move.api_name, move.name_en, move.name_de].flatMap(lookupKeys)
        .forEach((key) => this.pasteMoves.set(key, move.api_name));
    });
  }
}
