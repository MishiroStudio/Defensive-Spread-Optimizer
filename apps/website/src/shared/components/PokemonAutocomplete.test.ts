import { describe, expect, it } from 'vitest'

import {
  findPokemonSuggestions,
  localizedPokemonName,
} from './pokemonAutocompleteData'
import type { Pokemon } from '../types/pokemon'

const charizard: Pokemon = {
  dex: 6,
  pokemon_id: 6,
  api_name: 'charizard',
  name_en: 'Charizard',
  name_de: 'Glurak',
  types: ['fire', 'flying'],
  abilities: [],
  sprite_home: null,
  sprite_home_shiny: null,
  base_hp: 78,
  base_atk: 84,
  base_def: 78,
  base_spa: 109,
  base_spd: 85,
  base_spe: 100,
}

describe('Pokémon autocomplete localization', () => {
  it('finds an English query but displays the German name', () => {
    expect(
      findPokemonSuggestions([charizard], 'Char', 'de'),
    ).toEqual([
      {
        label: 'Glurak',
        pokemon: charizard,
      },
    ])
  })

  it('finds a German query but displays the English name', () => {
    expect(
      findPokemonSuggestions([charizard], 'Glu', 'en'),
    ).toEqual([
      {
        label: 'Charizard',
        pokemon: charizard,
      },
    ])
  })

  it('localizes the selected Pokémon independently of the query', () => {
    expect(localizedPokemonName(charizard, 'de')).toBe('Glurak')
    expect(localizedPokemonName(charizard, 'en')).toBe('Charizard')
  })
})
