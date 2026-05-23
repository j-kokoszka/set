import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import App from '../App'

// Mock fetch
const fetchMock = vi.fn()
globalThis.fetch = fetchMock as unknown as typeof fetch

describe('App Component', () => {
  it('renders login screen when unauthenticated', () => {
    // Ensure no token in localStorage
    localStorage.removeItem('set_token')
    
    // Mock successful fetch response for exercises
    fetchMock.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([])
    })

    render(<App />)
    
    expect(screen.getByText('set')).toBeInTheDocument()
    expect(screen.getByLabelText('Username')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Mock Login' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Sign in with Google/i })).toBeInTheDocument()
  })

  it('renders app header and tabs when authenticated', () => {
    // Mock authenticated state
    localStorage.setItem('set_token', 'mock_token')
    localStorage.setItem('set_user', 'testuser')
    
    // Mock successful fetch responses
    fetchMock.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([])
    })

    render(<App />)
    
    expect(screen.getByText('set')).toBeInTheDocument()
    expect(screen.getByText('testuser')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Log' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'History' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Routines' })).toBeInTheDocument()
  })
})
