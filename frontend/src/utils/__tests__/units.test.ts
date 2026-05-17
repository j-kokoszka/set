import { describe, it, expect } from 'vitest'
import { convertWeight } from '../units'

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
