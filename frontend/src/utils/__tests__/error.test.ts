import { describe, it, expect } from 'vitest'
import { parseBackendError } from '../error'

describe('parseBackendError', () => {
  it('extracts detail from JSON response', async () => {
    const mockResponse = {
      ok: false,
      status: 400,
      json: () => Promise.resolve({ detail: 'Invalid data' })
    } as Response
    
    const result = await parseBackendError(mockResponse, 'Default')
    expect(result).toBe('Default: Invalid data (Status: 400)')
  })

  it('extracts error from JSON response', async () => {
    const mockResponse = {
      ok: false,
      status: 401,
      json: () => Promise.resolve({ error: 'Auth failed' })
    } as Response
    
    const result = await parseBackendError(mockResponse, 'Default')
    expect(result).toBe('Default: Auth failed (Status: 401)')
  })

  it('falls back to default message if no detail or error', async () => {
    const mockResponse = {
      ok: false,
      status: 500,
      json: () => Promise.resolve({})
    } as Response
    
    const result = await parseBackendError(mockResponse, 'Generic error')
    expect(result).toBe('Generic error. Status: 500')
  })

  it('handles non-JSON responses gracefully', async () => {
    const mockResponse = {
      ok: false,
      status: 404,
      json: () => Promise.reject(new Error('Syntax error'))
    } as Response
    
    const result = await parseBackendError(mockResponse, 'Not found')
    expect(result).toBe('Not found. Status: 404')
  })
})
