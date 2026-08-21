import { describe, expect, it } from 'vitest'
import {
  applyDefensiveItem,
  applyStatStage,
  findBestDefensiveSpread,
} from './optimizer'

describe('applyStatStage', () => {
  it('leaves the stat unchanged at stage 0', () => {
    expect(applyStatStage(100, 0)).toBe(100)
  })

  it('applies positive stat stages', () => {
    expect(applyStatStage(100, 1)).toBe(150)
    expect(applyStatStage(100, 2)).toBe(200)
    expect(applyStatStage(100, 6)).toBe(400)
  })

  it('applies negative stat stages with integer rounding', () => {
    expect(applyStatStage(100, -1)).toBe(66)
    expect(applyStatStage(100, -2)).toBe(50)
    expect(applyStatStage(100, -6)).toBe(25)
  })

  it('rejects invalid stages', () => {
    expect(() => applyStatStage(100, 7)).toThrow(RangeError)
    expect(() => applyStatStage(100, -7)).toThrow(RangeError)
    expect(() => applyStatStage(100, 1.5)).toThrow(RangeError)
  })
})

describe('applyDefensiveItem', () => {
  it('changes nothing without an item', () => {
    expect(applyDefensiveItem(100, 101, 'none')).toEqual({
      defense: 100,
      specialDefense: 101,
    })
  })

  it('boosts both defensive stats with Eviolite', () => {
    expect(applyDefensiveItem(100, 101, 'eviolite')).toEqual({
      defense: 150,
      specialDefense: 151,
    })
  })

  it('boosts only Special Defense with Assault Vest', () => {
    expect(applyDefensiveItem(100, 101, 'assault_vest')).toEqual({
      defense: 100,
      specialDefense: 151,
    })
  })
})

describe('findBestDefensiveSpread', () => {
  it('finds the best defensive point distribution', () => {
    const pokemon = {
      base_hp: 100,
      base_atk: 100,
      base_def: 100,
      base_spa: 100,
      base_spd: 100,
      base_spe: 100,
    }

    const result = findBestDefensiveSpread(
      pokemon,
      'bulk',
      'attack',
    )

    expect(result).not.toBeNull()

    if (result === null) {
      throw new Error(
        'Expected a defensive spread',
      )
    }

    expect(result.nature.id).toBe('bold')

    expect(result.hp_points).toBe(32)
    expect(result.def_points).toBe(10)
    expect(result.spd_points).toBe(24)

    expect(result.hp).toBe(207)
    expect(result.defense).toBe(143)
    expect(result.special_defense).toBe(144)

    expect(
      result.hp_points
      + result.def_points
      + result.spd_points,
    ).toBe(66)
  })
})