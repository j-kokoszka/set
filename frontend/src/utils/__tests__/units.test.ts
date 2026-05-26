import { describe, it, expect } from 'vitest'
import { convertWeight, calculate1RM } from '../units'

describe('convertWeight', () => {
  it('converts kg to lbs correctly', () => {
    expect(convertWeight(10, 'lbs')).toBe(22.0)
    expect(convertWeight(100, 'lbs')).toBe(220.5)
  })

  it('converts lbs to kg correctly', () => {
    expect(convertWeight(22.0, 'kg')).toBe(10)
    expect(convertWeight(220.5, 'kg')).toBe(100)
  })

  it('returns 0 for zero or negative weight', () => {
    expect(convertWeight(0, 'lbs')).toBe(0)
    expect(convertWeight(-10, 'kg')).toBe(0)
  })
})

describe('calculate1RM', () => {
  it('calculates 1RM correctly for standard cases', () => {
    expect(calculate1RM(100, 1)).toBe(100)
    // McGlothin: 100 * (36 / (37 - 10)) = 100 * (36 / 27) = 100 * 1.333... = 133.33...
    expect(calculate1RM(100, 10)).toBeCloseTo(133.33, 1)
  })

  it('handles 0 or negative reps', () => {
    expect(calculate1RM(100, 0)).toBe(0)
    expect(calculate1RM(100, -5)).toBe(0)
  })

  it('caps reps at 36 to avoid crash', () => {
    // 37 reps would be division by zero in original formula
    expect(calculate1RM(100, 37)).toBe(calculate1RM(100, 36))
    expect(isFinite(calculate1RM(100, 37))).toBe(true)
  })
})
