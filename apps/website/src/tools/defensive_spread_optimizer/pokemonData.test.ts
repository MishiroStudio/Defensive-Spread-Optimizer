import { describe, expect, it } from 'vitest'

import { flattenPokemonData } from './pokemonData'

describe('flattenPokemonData', () => {
  it('converts nested Pokédex forms into optimizer Pokémon', () => {
    const result = flattenPokemonData([
      {
        dex: 1,
        api_name: 'bulbasaur',
        name_en: 'Bulbasaur',
        name_de: 'Bisasam',
        forms: [
          {
            pokemon_id: 1,
            api_name: 'bulbasaur',
            name_en: 'Bulbasaur',
            name_de: 'Bisasam',
            is_default: true,
            base_stats: {
              hp: 45,
              atk: 49,
              def: 49,
              spa: 65,
              spd: 65,
              spe: 45,
            },
            sprites: {
              home:
                'assets/sprites/home/normal/bulbasaur.png',
              home_shiny:
                'assets/sprites/home/shiny/bulbasaur.png',
            },
          },
        ],
      },
    ])

    expect(result).toEqual([
      {
        dex: 1,
        pokemon_id: 1,
        api_name: 'bulbasaur',
        name_en: 'Bulbasaur',
        name_de: 'Bisasam',
        sprite_home:
          'assets/sprites/home/normal/bulbasaur.png',
        sprite_home_shiny:
          'assets/sprites/home/shiny/bulbasaur.png',
        base_hp: 45,
        base_atk: 49,
        base_def: 49,
        base_spa: 65,
        base_spd: 65,
        base_spe: 45,
      },
    ])
  })

  it('rejects data without a forms array', () => {
    expect(() => flattenPokemonData([
      {
        dex: 1,
      },
    ])).toThrow('must contain a forms array')
  })

  it('rejects a non-array root value', () => {
    expect(() => flattenPokemonData({})).toThrow(
      'Pokémon data must be an array',
    )
  })
})
