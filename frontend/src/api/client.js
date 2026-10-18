import { useViewerStore } from '../stores/viewer'

const BASE_URL = '/api/v1'

export class ApiError extends Error {
  constructor(status, envelope) {
    super(envelope?.error?.message || `request failed with status ${status}`)
    this.status = status
    this.code = envelope?.error?.code
    this.requestId = envelope?.error?.request_id
  }
}

async function request(method, path, { params, body, signal } = {}) {
  const viewer = useViewerStore()
  const url = new URL(BASE_URL + path, window.location.origin)
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) url.searchParams.set(key, value)
    }
  }

  const response = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json', 'X-Viewer-Id': viewer.viewerId },
    body: body ? JSON.stringify(body) : undefined,
    signal,
  })

  if (response.status === 204) return null

  const payload = await response.json().catch(() => null)
  if (!response.ok) throw new ApiError(response.status, payload)
  return payload
}

export const api = {
  searchShows: (q, limit = 20, signal, genre) =>
    request('GET', '/shows/search', { params: { q, limit, genre }, signal }),
  // `cursor` is the opaque next_cursor from the previous page; omitted it starts
  // at the top of the ranking.
  popularShows: (limit = 20, signal, genre, cursor) =>
    request('GET', '/shows/popular', { params: { limit, genre, cursor }, signal }),
  genres: (signal) => request('GET', '/shows/genres', { signal }),
  showDetails: (showId) => request('GET', `/shows/${showId}`),
  watchedEpisodes: (showId) => request('GET', '/viewers/me/watched', { params: { show_id: showId } }),
  markWatched: (episodeId) => request('PUT', `/viewers/me/watched/${episodeId}`),
  unmarkWatched: (episodeId) => request('DELETE', `/viewers/me/watched/${episodeId}`),
  listComments: (targetType, targetId) =>
    request('GET', '/comments', { params: { target_type: targetType, target_id: targetId } }),
  postComment: (targetType, targetId, body) =>
    request('POST', '/comments', { body: { target_type: targetType, target_id: targetId, body } }),
  generateInsight: (targetType, targetId) =>
    request('POST', '/insights', { body: { target_type: targetType, target_id: targetId } }),
  peekInsight: (targetType, targetId) =>
    request('GET', '/insights', { params: { target_type: targetType, target_id: targetId } }),
}
