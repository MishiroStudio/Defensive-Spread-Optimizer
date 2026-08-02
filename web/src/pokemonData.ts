import type { Pokemon } from './types/pokemon'

export async function loadPokemonData(): Promise<Pokemon[]> {
  const dataUrl = `${import.meta.env.BASE_URL}data/pokemon.json`

  const response = await fetch(dataUrl)

  if (!response.ok) {
    throw new Error(
      `Pokémon data could not be loaded: ${response.status}`,
    )
  }

  const data: unknown = await response.json()

  if (!Array.isArray(data)) {
    throw new TypeError(
      'Pokémon data must be an array.',
    )
  }

  return data as Pokemon[]
}