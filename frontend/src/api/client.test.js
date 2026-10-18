import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { api } from './client'

beforeEach(() => {
  localStorage.clear()
  setActivePinia(createPinia())
})

describe('API contract', () => {
  it('sends search filters and viewer identity', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: true, status: 200, json: async () => ({ items: [] }) })
    const signal = new AbortController().signal

    await api.searchShows('dex', 20, signal, 'Drama')

    const [url, options] = fetchMock.mock.calls[0]
    expect(url.pathname).toBe('/api/v1/shows/search')
    expect(url.search).toBe('?q=dex&limit=20&genre=Drama')
    expect(options.signal).toBe(signal)
    expect(options.headers['X-Viewer-Id']).toMatch(/^[0-9a-f-]{36}$/)
    expect(localStorage.getItem('tv-series-search:viewer-id')).toBe(options.headers['X-Viewer-Id'])
  })

  it('passes the opaque cursor to the next popular page', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: true, status: 200, json: async () => ({ items: [] }) })

    await api.popularShows(20, undefined, 'Comedy', 'opaque+cursor')

    expect(fetchMock.mock.calls[0][0].search).toBe('?limit=20&genre=Comedy&cursor=opaque%2Bcursor')
  })

  it('sends a comment as JSON and returns the created comment', async () => {
    const created = { id: 8, body: 'Great', viewer_id: 'viewer' }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: true, status: 201, json: async () => created })

    expect(await api.postComment('show', 12, 'Great')).toEqual(created)

    const [, options] = fetchMock.mock.calls[0]
    expect(options.method).toBe('POST')
    expect(JSON.parse(options.body)).toEqual({ target_type: 'show', target_id: 12, body: 'Great' })
  })

  it('returns null for a 204 response without parsing JSON', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: true, status: 204, json: () => { throw new Error('must not parse') } })
    expect(await api.unmarkWatched(4)).toBeNull()
  })

  it('exposes the server error envelope', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false, status: 503,
      json: async () => ({ error: { code: 'UPSTREAM_DOWN', message: 'Unavailable', request_id: 'req-1' } }),
    })

    await expect(api.genres()).rejects.toMatchObject({
      status: 503, code: 'UPSTREAM_DOWN', message: 'Unavailable', requestId: 'req-1',
    })
  })
})
