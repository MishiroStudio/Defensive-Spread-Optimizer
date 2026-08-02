import { describe, expect, it } from 'vitest'
import {
  calculateAttack,
  calculateDefense,
  calculateHp,
  calculateOtherStat,
  calculateSpecialAttack,
  calculateSpecialDefense,
  calculateSpeed,
} from './stats'

describe('calculateHp', () => {
  it('calculates a level 50 HP stat', () => {
    expect(calculateHp(100, 0)).toBe(175)
  })

  it('adds the selected stat points', () => {
    expect(calculateHp(100, 32)).toBe(207)
  })
})

describe('calculateOtherStat', () => {
  it('calculates a neutral level 50 stat', () => {
    expect(calculateOtherStat(100, 0)).toBe(120)
  })

  it('applies an increased nature and rounds down', () => {
    expect(calculateOtherStat(101, 0, 1.1)).toBe(133)
  })

  it('applies a decreased nature and rounds down', () => {
    expect(calculateOtherStat(101, 0, 0.9)).toBe(108)
  })

  it('adds stat points before applying the nature', () => {
    expect(calculateOtherStat(100, 10, 1.1)).toBe(143)
  })
})

describe('individual stat functions', () => {
  it('uses the same formula for every non-HP stat', () => {
    expect(calculateAttack(100, 5, 1.1)).toBe(137)
    expect(calculateDefense(100, 5, 1.1)).toBe(137)
    expect(calculateSpecialAttack(100, 5, 1.1)).toBe(137)
    expect(calculateSpecialDefense(100, 5, 1.1)).toBe(137)
    expect(calculateSpeed(100, 5, 1.1)).toBe(137)
  })
})