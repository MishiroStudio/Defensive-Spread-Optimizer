export interface PokemonBaseStats {
  hp: number
  atk: number
  def: number
  spa: number
  spd: number
  spe: number
}

export interface PokemonSprites {
  home: string | null
  home_shiny: string | null
}

export interface PokemonAbility {
  api_name: string
  name_en: string
  name_de: string
  is_hidden: boolean
  slot: number
}

export interface PokemonForm {
  pokemon_id: number
  api_name: string
  name_en: string
  name_de: string
  is_default: boolean
  types: string[]
  abilities: PokemonAbility[]
  base_stats: PokemonBaseStats
  sprites: PokemonSprites
}

export interface PokemonSpecies {
  dex: number
  api_name: string
  name_en: string
  name_de: string
  forms: PokemonForm[]
}

/**
 * Flat Pokémon-form view used internally by the Defensive Spread Optimizer.
 */
export interface Pokemon {
  dex: number
  pokemon_id: number
  api_name: string

  name_en: string
  name_de: string

  types: string[]

  sprite_home: string | null
  sprite_home_shiny: string | null

  base_hp: number
  base_atk: number
  base_def: number
  base_spa: number
  base_spd: number
  base_spe: number
}
