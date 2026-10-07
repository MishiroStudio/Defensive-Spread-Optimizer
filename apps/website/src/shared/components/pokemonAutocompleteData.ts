import type { Pokemon } from '../types/pokemon'

export type PokemonDisplayLanguage = 'de' | 'en'

export interface PokemonNameOption {
  label: string
  pokemon: Pokemon
}

function normalizeName(value: string): string {
  return value
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
    .toLocaleLowerCase()
}

function matchRank(
  pokemon: Pokemon,
  query: string,
): number | null {
  const normalizedQuery = normalizeName(query)

  if (normalizedQuery === '') {
    return null
  }

  if (/^\d+$/.test(normalizedQuery)) {
    return pokemon.dex === Number(normalizedQuery)
      ? 0
      : null
  }

  const names = [
    pokemon.name_de,
    pokemon.name_en,
    pokemon.api_name,
  ]
    .map(normalizeName)
    .filter(Boolean)

  if (names.includes(normalizedQuery)) {
    return 0
  }

  if (names.some((name) => name.startsWith(normalizedQuery))) {
    return 1
  }

  if (names.some((name) => name.includes(normalizedQuery))) {
    return 2
  }

  return null
}

export function localizedPokemonName(
  pokemon: Pokemon,
  language: PokemonDisplayLanguage,
): string {
  return language === 'de'
    ? pokemon.name_de || pokemon.name_en
    : pokemon.name_en || pokemon.name_de
}

export function findPokemonSuggestions(
  pokemonList: Pokemon[],
  query: string,
  language: PokemonDisplayLanguage,
  limit = 12,
): PokemonNameOption[] {
  return pokemonList
    .map((pokemon) => ({
      pokemon,
      rank: matchRank(pokemon, query),
    }))
    .filter((entry): entry is { pokemon: Pokemon; rank: number } => (
      entry.rank !== null
    ))
    .toSorted((left, right) => (
      left.rank - right.rank
      || localizedPokemonName(left.pokemon, language)
        .localeCompare(
          localizedPokemonName(right.pokemon, language),
          language,
        )
    ))
    .slice(0, limit)
    .map(({ pokemon }) => ({
      pokemon,
      label: localizedPokemonName(pokemon, language),
    }))
}
