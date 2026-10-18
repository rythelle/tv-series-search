import { defineStore } from 'pinia'

const STORAGE_KEY = 'tv-series-search:viewer-id'

function loadOrCreateViewerId() {
  const existing = localStorage.getItem(STORAGE_KEY)
  if (existing) return existing
  const generated = crypto.randomUUID()
  localStorage.setItem(STORAGE_KEY, generated)
  return generated
}

export const useViewerStore = defineStore('viewer', {
  state: () => ({
    viewerId: loadOrCreateViewerId(),
    watchedEpisodeIds: new Set(),
  }),
  actions: {
    setWatched(episodeIds) {
      this.watchedEpisodeIds = new Set(episodeIds)
    },
    markWatched(episodeId) {
      this.watchedEpisodeIds.add(episodeId)
    },
    unmarkWatched(episodeId) {
      this.watchedEpisodeIds.delete(episodeId)
    },
    isWatched(episodeId) {
      return this.watchedEpisodeIds.has(episodeId)
    },
  },
})
