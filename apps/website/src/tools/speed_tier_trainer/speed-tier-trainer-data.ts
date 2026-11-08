// speed-tier-trainer-data.ts — Speed Tier Trainer PWA V2
import { calculateOtherStat } from "../../shared/calculations/stats";
import type {
  Language,
  PokemonForm,
  PokemonSpecies,
  Regulation,
  RegulationsData,
} from "../pokedex/pokedex-data";
import { publicPath } from "../pokedex/public-path";

export type UsageLimit = 10 | 25 | 50 | 100 | null;
export type AnswerDirection = "exact" | "low" | "high" | "revealed";

export interface UsageEntry {
  rank: number;
  pokemon_id: number;
  api_name: string;
  showdown_id: string;
  showdown_name: string;
  usage_percent: number;
}

export interface UsageDataset {
  format_id: string;
  month: string;
  rating_cutoff: number;
  total_battles: number;
  source_url: string;
  entries: UsageEntry[];
}

export interface UsageStatsData {
  schema_version: number;
  current_regulation_id: string;
  formats: Record<string, UsageDataset>;
}

export interface TrainerBundle {
  pokemon: PokemonSpecies[];
  regulations: RegulationsData;
  usage: UsageStatsData;
}

export interface TrainerScope {
  key: string;
  labelDe: string;
  labelEn: string;
  pokemonIds: ReadonlySet<number>;
}

export interface AnswerResult {
  pokemon: PokemonForm;
  guess: number | null;
  difference: number | null;
  direction: AnswerDirection;
}

export interface SpeedValues {
  minimumNeutral: number;
  minimumDecreased: number;
  maximumNeutral: number;
  maximumIncreased: number;
  choiceScarfNeutral: number;
  choiceScarfIncreased: number;
}

export interface TrainerSessionOptions {
  finite?: boolean;
  random?: () => number;
}

const MEGA_BASE_OVERRIDES: Record<string, string> = {
  "floette-mega": "floette-eternal",
  "pyroar-mega": "pyroar-male",
};

export const USAGE_LIMITS = [100, 50, 25, 10] as const;

export function displayName(pokemon: PokemonForm, language: Language): string {
  return language === "en" ? pokemon.name_en : pokemon.name_de;
}

export function calculateSpeedValues(baseSpeed: number): SpeedValues {
  const maximumNeutral = calculateOtherStat(baseSpeed, 32, 1);
  const maximumIncreased = calculateOtherStat(baseSpeed, 32, 1.1);
  return {
    minimumNeutral: calculateOtherStat(baseSpeed, 0, 1),
    minimumDecreased: calculateOtherStat(baseSpeed, 0, 0.9),
    maximumNeutral,
    maximumIncreased,
    choiceScarfNeutral: Math.floor(maximumNeutral * 1.5),
    choiceScarfIncreased: Math.floor(maximumIncreased * 1.5),
  };
}

export function answerResultFor(
  pokemon: PokemonForm,
  guess: number | null,
): AnswerResult {
  const difference = guess === null ? null : guess - pokemon.base_stats.spe;
  const direction: AnswerDirection = difference === null
    ? "revealed"
    : difference === 0
      ? "exact"
      : difference < 0 ? "low" : "high";
  return { pokemon, guess, difference, direction };
}

export async function loadTrainerBundle(
  signal?: AbortSignal,
): Promise<TrainerBundle> {
  const files = ["pokemon_v2", "regulations", "usage_stats"] as const;
  const responses = await Promise.all(files.map((name) => fetch(
    publicPath(`data/${name}.json`),
    { signal },
  )));
  for (const response of responses) {
    if (!response.ok) {
      throw new Error(`Trainer-Daten konnten nicht geladen werden (${response.status}).`);
    }
  }
  const [pokemon, regulations, usage] = await Promise.all(
    responses.map((response) => response.json()),
  );
  return {
    pokemon: pokemon as PokemonSpecies[],
    regulations: regulations as RegulationsData,
    usage: usage as UsageStatsData,
  };
}

function regulationSort(left: Regulation, right: Regulation): number {
  return (right.year ?? 0) - (left.year ?? 0)
    || (right.code ?? right.name).localeCompare(left.code ?? left.name);
}

function megaBaseName(apiName: string): string {
  if (!apiName.includes("-mega")) return apiName;
  return MEGA_BASE_OVERRIDES[apiName] ?? apiName.split("-mega", 1)[0];
}

export class TrainerCatalog {
  readonly entries: PokemonForm[];
  readonly scopes: TrainerScope[];
  readonly currentRegulationId: string;
  private readonly usage: UsageStatsData;
  private readonly entriesById = new Map<number, PokemonForm>();

  constructor(bundle: TrainerBundle) {
    this.currentRegulationId = bundle.regulations.current_regulation_id;
    this.usage = bundle.usage;
    this.entries = bundle.pokemon.flatMap((species) => species.forms.map((form) => ({
      ...form,
      national_dex: species.dex,
      evolves_from_species_id: species.evolves_from_species_id,
    }))).toSorted((left, right) => (
      left.national_dex - right.national_dex
      || left.pokemon_id - right.pokemon_id
    ));
    this.entries.forEach((entry) => this.entriesById.set(entry.pokemon_id, entry));
    this.scopes = this.buildScopes(bundle.regulations);
  }

  private buildScopes(regulations: RegulationsData): TrainerScope[] {
    const byId = new Map(regulations.regulations.map((item) => [item.id, item]));
    const current = byId.get(regulations.current_regulation_id)
      ?? regulations.regulations.toSorted(regulationSort)[0];
    if (!current) throw new Error("Keine verwendbare Regulation gefunden.");

    const scopeFor = (regulation: Regulation): TrainerScope => ({
      key: regulation.id,
      labelDe: regulation.name,
      labelEn: regulation.name,
      pokemonIds: new Set(regulation.pokemon_ids),
    });
    const allIds = new Set(this.entries.map((entry) => entry.pokemon_id));
    const historical = regulations.regulations
      .filter((item) => item.id !== current.id)
      .toSorted(regulationSort);

    return [
      scopeFor(current),
      {
        key: "all",
        labelDe: "Nationaler Dex",
        labelEn: "National Dex",
        pokemonIds: allIds,
      },
      ...historical.map(scopeFor),
    ];
  }

  scopeLabel(scope: TrainerScope, language: Language): string {
    return language === "en" ? scope.labelEn : scope.labelDe;
  }

  usageDatasetForScope(scopeKey: string): UsageDataset | null {
    const usageScope = scopeKey === "all" ? this.currentRegulationId : scopeKey;
    return this.usage.formats[usageScope] ?? null;
  }

  entriesForScope(
    scopeKey: string,
    usageLimit: UsageLimit = null,
  ): PokemonForm[] {
    const scope = this.scopes.find((item) => item.key === scopeKey);
    if (!scope) throw new Error(`Unbekannte Pokémon-Auswahl: ${scopeKey}`);
    const scopeEntries = this.entries.filter((entry) => scope.pokemonIds.has(entry.pokemon_id));
    if (usageLimit === null) return scopeEntries;

    const dataset = this.usageDatasetForScope(scopeKey);
    if (!dataset) throw new Error("Für diese Auswahl sind keine Usage-Daten verfügbar.");
    const allowed = new Map(scopeEntries.map((entry) => [entry.pokemon_id, entry]));
    return dataset.entries
      .map((entry) => allowed.get(entry.pokemon_id))
      .filter((entry): entry is PokemonForm => entry !== undefined)
      .slice(0, usageLimit);
  }

  megaVariants(pokemon: PokemonForm, scopeKey: string): PokemonForm[] {
    const scopeEntries = this.entriesForScope(scopeKey);
    const entriesByName = new Map(scopeEntries.map((entry) => [entry.api_name, entry]));
    const baseApiName = megaBaseName(pokemon.api_name);
    const baseForm = entriesByName.get(baseApiName);
    if (!baseForm) return [pokemon];

    const megaForms = scopeEntries
      .filter((entry) => (
        entry.api_name.includes("-mega")
        && megaBaseName(entry.api_name) === baseApiName
      ))
      .toSorted((left, right) => left.api_name.localeCompare(right.api_name));
    const variants = [baseForm, ...megaForms];
    if (variants.length < 2 || !variants.some((entry) => entry.pokemon_id === pokemon.pokemon_id)) {
      return [pokemon];
    }
    return variants;
  }

  entryById(pokemonId: number): PokemonForm | null {
    return this.entriesById.get(pokemonId) ?? null;
  }
}

export function shuffledDeck<T>(
  pool: readonly T[],
  random: () => number = Math.random,
  avoidFirst?: T,
): T[] {
  const deck = [...pool];
  for (let index = deck.length - 1; index > 0; index -= 1) {
    const target = Math.floor(random() * (index + 1));
    [deck[index], deck[target]] = [deck[target], deck[index]];
  }
  if (avoidFirst !== undefined && deck.length > 1 && deck[0] === avoidFirst) {
    [deck[0], deck[1]] = [deck[1], deck[0]];
  }
  return deck;
}

export class TrainerSession {
  private readonly pool: readonly PokemonForm[];
  private readonly random: () => number;
  private deck: PokemonForm[];
  private index = 0;
  private answeredCurrent = false;
  private results: AnswerResult[] = [];

  readonly finite: boolean;

  answered = 0;
  guessed = 0;
  exact = 0;
  totalAbsoluteError = 0;
  currentStreak = 0;
  bestStreak = 0;

  constructor(
    pokemon: readonly PokemonForm[],
    options: TrainerSessionOptions = {},
  ) {
    if (pokemon.length === 0) throw new Error("Die ausgewählte Pokémon-Gruppe ist leer.");
    this.pool = [...pokemon];
    this.random = options.random ?? Math.random;
    this.finite = options.finite ?? false;
    this.deck = shuffledDeck(this.pool, this.random);
  }

  get current(): PokemonForm {
    return this.deck[this.index];
  }

  get currentAnswered(): boolean {
    return this.answeredCurrent;
  }

  get isComplete(): boolean {
    return this.finite
      && this.answeredCurrent
      && this.index === this.deck.length - 1;
  }

  get roundPokemon(): readonly PokemonForm[] {
    return [...this.pool];
  }

  get incorrectPokemon(): readonly PokemonForm[] {
    const incorrect = new Map<number, PokemonForm>();
    for (const result of this.results) {
      if (result.direction !== "exact") {
        incorrect.set(result.pokemon.pokemon_id, result.pokemon);
      }
    }
    return [...incorrect.values()];
  }

  get questionNumber(): number {
    return this.answeredCurrent ? this.answered : this.answered + 1;
  }

  get accuracy(): number {
    return this.answered > 0 ? this.exact / this.answered : 0;
  }

  private recalculateStats(): void {
    this.answered = this.results.length;
    this.guessed = 0;
    this.exact = 0;
    this.totalAbsoluteError = 0;
    this.currentStreak = 0;
    this.bestStreak = 0;

    for (const result of this.results) {
      if (result.difference !== null) {
        this.guessed += 1;
        this.totalAbsoluteError += Math.abs(result.difference);
      }
      if (result.direction === "exact") {
        this.exact += 1;
        this.currentStreak += 1;
        this.bestStreak = Math.max(this.bestStreak, this.currentStreak);
      } else {
        this.currentStreak = 0;
      }
    }
  }

  submit(guess: number | null, pokemon: PokemonForm = this.current): AnswerResult {
    if (this.answeredCurrent) throw new Error("Die aktuelle Frage wurde bereits beantwortet.");
    if (guess !== null && (!Number.isInteger(guess) || guess < 1 || guess > 255)) {
      throw new Error("Die Antwort muss zwischen 1 und 255 liegen.");
    }

    const result = answerResultFor(pokemon, guess);
    this.results.push(result);
    this.recalculateStats();
    this.answeredCurrent = true;
    return result;
  }

  recalculateCurrentResult(pokemon: PokemonForm): AnswerResult {
    if (!this.answeredCurrent || this.results.length === 0) {
      throw new Error("Die aktuelle Frage wurde noch nicht beantwortet.");
    }
    const previous = this.results.at(-1)!;
    const result = answerResultFor(pokemon, previous.guess);
    this.results[this.results.length - 1] = result;
    this.recalculateStats();
    return result;
  }

  advance(): void {
    if (!this.answeredCurrent) throw new Error("Die aktuelle Frage ist noch nicht beantwortet.");
    if (this.isComplete) throw new Error("Die Runde ist bereits abgeschlossen.");
    const previous = this.current;
    this.index += 1;
    if (this.index >= this.deck.length) {
      this.deck = shuffledDeck(this.pool, this.random, previous);
      this.index = 0;
    }
    this.answeredCurrent = false;
  }
}
