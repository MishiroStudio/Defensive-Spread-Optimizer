import { describe, expect, it } from 'vitest'
import { calculateSimpleDamage } from './damage'

describe('calculateSimpleDamage', () => {
  it('calculates the reference damage', () => {
    expect(calculateSimpleDamage(100)).toBe(100)
    expect(calculateSimpleDamage(200)).toBe(50)
    expect(calculateSimpleDamage(250)).toBe(40)
  })

  it('returns less damage for a higher defensive stat', () => {
    const lowerDefenseDamage =
      calculateSimpleDamage(100)

    const higherDefenseDamage =
      calculateSimpleDamage(150)

    expect(higherDefenseDamage).toBeLessThan(
      lowerDefenseDamage,
    )
  })

  it('preserves decimal results', () => {
    expect(calculateSimpleDamage(120)).toBeCloseTo(
      83.333333,
      5,
    )
  })
})