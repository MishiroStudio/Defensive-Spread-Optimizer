export interface Pokemon {
  dex: number
  pokemon_id: number
  api_name: string

  name_en: string
  name_de: string

  sprite_home: string | null
  sprite_home_shiny: string | null

  base_hp: number
  base_atk: number
  base_def: number
  base_spa: number
  base_spd: number
  base_spe: number
}