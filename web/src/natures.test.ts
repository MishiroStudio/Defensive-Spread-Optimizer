import { describe, expect, it } from 'vitest'
import {
  getNaturesByStatChanges,
  NATURES,
} from './natures'

describe('getNaturesByStatChanges', () => {
  it('contains all 25 Pokémon natures', () => {
    expect(Object.keys(NATURES)).toHaveLength(25)
  })

  it('finds a specific nature', () => {
    const result = getNaturesByStatChanges(
      'defense',
      'attack',
    )

    expect(result).toEqual({
      bold: NATURES.bold,
    })
  })

  it('finds both defensive options for bulk', () => {
    const result = getNaturesByStatChanges(
      'bulk',
      'attack',
    )

    expect(Object.keys(result).sort()).toEqual([
      'bold',
      'calm',
    ])
  })

  it('ignores capitalization and whitespace', () => {
    const result = getNaturesByStatChanges(
      '  DEFENSE ',
      ' SPECIAL_ATTACK  ',
    )

    expect(result).toEqual({
      impish: NATURES.impish,
    })
  })

  it('returns an empty object for an unsupported combination', () => {
    const result = getNaturesByStatChanges(
      'defense',
      'defense',
    )

    expect(result).toEqual({})
  })

  it('does not return the neutral Hardy nature', () => {
    const result = getNaturesByStatChanges(
      'bulk',
      'speed',
    )

    expect(result.hardy).toBeUndefined()
  })
})