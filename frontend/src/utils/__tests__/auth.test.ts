import { describe, it, expect } from 'vitest'
import { generateCodeVerifier, generateCodeChallenge, base64UrlDecode } from '../auth'

describe('Auth Utilities', () => {
  describe('generateCodeVerifier', () => {
    it('generates a string of correct length', () => {
      const verifier = generateCodeVerifier()
      // 56 Uint32 entries converted to hex strings (2 chars each)
      expect(verifier.length).toBe(112)
    })

    it('generates unique values', () => {
      const v1 = generateCodeVerifier()
      const v2 = generateCodeVerifier()
      expect(v1).not.toBe(v2)
    })
  })

  describe('generateCodeChallenge', () => {
    it('generates a valid base64url challenge', async () => {
      const verifier = 'test-verifier-string'
      const challenge = await generateCodeChallenge(verifier)
      
      // Should not contain URL-unsafe characters
      expect(challenge).not.toContain('+')
      expect(challenge).not.toContain('/')
      expect(challenge).not.not.toContain('=')
      expect(challenge.length).toBeGreaterThan(0)
    })
  })

  describe('base64UrlDecode', () => {
    it('decodes standard base64 correctly', () => {
      // {"sub":"123","name":"John"}
      const token = 'eyJzdWIiOiIxMjMiLCJuYW1lIjoiSm9obiJ9'
      const decoded = base64UrlDecode(token)
      expect(decoded).toEqual({ sub: '123', name: 'John' })
    })

    it('decodes base64url with special characters correctly', () => {
      // {"id":1,"msg":"hello-world?"}
      // base64: eyJpZCI6MSwibXNnIjoiaGVsbG8td29ybGQ_In0=
      // base64url: eyJpZCI6MSwibXNnIjoiaGVsbG8td29ybGQ_In0
      const token = 'eyJpZCI6MSwibXNnIjoiaGVsbG8td29ybGQ_In0'
      const decoded = base64UrlDecode(token)
      expect(decoded).toEqual({ id: 1, msg: 'hello-world?' })
    })

    it('returns null for invalid base64', () => {
      const decoded = base64UrlDecode('!!!invalid!!!')
      expect(decoded).toBeNull()
    })
  })
})
