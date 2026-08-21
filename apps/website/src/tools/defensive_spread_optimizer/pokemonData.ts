import type {
  Pokemon,
  PokemonSpecies,
} from '../../shared/types/pokemon'

export function flattenPokemonData(
  data: unknown,
): Pokemon[] {
  if (!Array.isArray(data)) {
    throw new TypeError(
      'Pokémon data must be an array.',
    )
  }

  const speciesList = data as PokemonSpecies[]

  return speciesList.flatMap((species) => {
    if (!Array.isArray(species.forms)) {
      throw new TypeError(
        `Pokémon #${species.dex} must contain a forms array.`,
      )
    }

    return species.forms.map((form) => ({
      dex: species.dex,
      pokemon_id: form.pokemon_id,
      api_name: form.api_name,
      name_en: form.name_en,
      name_de: form.name_de,
      sprite_home: form.sprites.home,
      sprite_home_shiny: form.sprites.home_shiny,
      base_hp: form.base_stats.hp,
      base_atk: form.base_stats.atk,
      base_def: form.base_stats.def,
      base_spa: form.base_stats.spa,
      base_spd: form.base_stats.spd,
      base_spe: form.base_stats.spe,
    }))
  })
}

export async function loadPokemonData(): Promise<Pokemon[]> {
  const dataUrl =
    `${import.meta.env.BASE_URL}data/pokemon_v2.json`

  const response = await fetch(dataUrl)

  if (!response.ok) {
    throw new Error(
      `Pokémon data could not be loaded: ${response.status}`,
    )
  }

  const data: unknown = await response.json()

  return flattenPokemonData(data)
}