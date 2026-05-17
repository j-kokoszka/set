import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import App from '../App'

// Mock fetch
global.fetch = vi.fn()

describe('App Component', () => {
  it('renders login screen when unauthenticated', () => {
    // Ensure no token in localStorage
    localStorage.removeItem('set_token')
    
    render(<App />)
    
    expect(screen.getByText('set')).toBeInTheDocument()
    expect(screen.getByLabelText('Username')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Login' })).toBeInTheDocument()
  })

  it('renders app header and tabs when authenticated', () => {
    // Mock authenticated state
    localStorage.setItem('set_token', 'mock_token')
    localStorage.setItem('set_user', 'testuser')
    
    // Mock successful fetch responses
    ;(global.fetch as unknown as { mockResolvedValue: (v: unknown) => void }).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([])
    })

    render(<App />)
    
    expect(screen.getByText('set')).toBeInTheDocument()
    expect(screen.getByText('testuser')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Log' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'History' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Plans' })).toBeInTheDocument()
  })
})
