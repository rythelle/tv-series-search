import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createPinia } from 'pinia'
import SearchView from './SearchView.vue'
import { api } from '../api/client'

vi.mock('../api/client', () => ({
  api: {
    popularShows: vi.fn(), searchShows: vi.fn(), genres: vi.fn(),
    showDetails: vi.fn(), watchedEpisodes: vi.fn(), listComments: vi.fn(), peekInsight: vi.fn(),
  },
}))

const show = (id, name) => ({ id, name, poster_url: null, premiered_year: 2020, genres: ['Drama'] })
let wrapper
let observers

class TestObserver {
  constructor(callback) { this.callback = callback; observers.push(this) }
  observe() {}
  unobserve() {}
  disconnect() {}
  enter() { this.callback([{ isIntersecting: true }]) }
}

async function render() {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', name: 'search', component: SearchView }] })
  await router.push('/')
  await router.isReady()
  wrapper = mount(SearchView, { attachTo: document.body, global: { plugins: [createPinia(), router] } })
  await flushPromises()
  return { wrapper, router }
}

beforeEach(() => {
  observers = []
  vi.stubGlobal('IntersectionObserver', TestObserver)
  api.popularShows.mockReset().mockResolvedValue({ items: [show(1, 'First Show')], total: 2, next_cursor: 'page-2', degraded: false })
  api.searchShows.mockReset().mockResolvedValue({ items: [show(2, 'Second Show')], total: 1, next_cursor: null, degraded: false })
  api.genres.mockReset().mockResolvedValue({ items: ['Drama', 'Comedy'] })
  api.showDetails.mockReset().mockResolvedValue({ show: show(1, 'First Show'), seasons: [], degraded: false })
  api.watchedEpisodes.mockReset().mockResolvedValue({ episode_ids: [] })
  api.listComments.mockReset().mockResolvedValue({ items: [] })
  api.peekInsight.mockReset().mockResolvedValue(null)
})

afterEach(() => {
  wrapper?.unmount()
  wrapper = null
  document.body.innerHTML = ''
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('search and browsing', () => {
  it('shows the first shelf page and loads more with the opaque cursor', async () => {
    const { wrapper } = await render()
    expect(wrapper.text()).toContain('First Show')
    expect(wrapper.text()).toContain('1 of 2 titles')

    api.popularShows.mockResolvedValueOnce({ items: [show(2, 'Second Show')], total: 2, next_cursor: null, degraded: false })
    observers[0].enter()
    await flushPromises()

    expect(api.popularShows).toHaveBeenLastCalledWith(20, expect.any(AbortSignal), undefined, 'page-2')
    expect(wrapper.text()).toContain('First Show')
    expect(wrapper.text()).toContain('Second Show')
    expect(wrapper.text()).toContain('Search by name to reach titles beyond it.')
  })

  it('filters by genre and clears filters back to the shelf', async () => {
    const { wrapper } = await render()
    vi.useFakeTimers()

    await wrapper.get('#genre-select').setValue('Drama')
    await vi.runAllTimersAsync()
    await flushPromises()
    expect(api.popularShows).toHaveBeenLastCalledWith(20, expect.any(AbortSignal), 'Drama', undefined)

    await wrapper.get('#search-input').setValue('Dex')
    await vi.runAllTimersAsync()
    await flushPromises()
    expect(api.searchShows).toHaveBeenLastCalledWith('Dex', 20, expect.any(AbortSignal), 'Drama')
    expect(wrapper.text()).toContain('Second Show')

    await wrapper.get('.clear-filters').trigger('click')
    await vi.runAllTimersAsync()
    await flushPromises()
    expect(wrapper.get('#search-input').element.value).toBe('')
    expect(wrapper.get('#genre-select').element.value).toBe('')
    expect(api.popularShows).toHaveBeenLastCalledWith(20, expect.any(AbortSignal), undefined, undefined)
  })

  it('shows the degraded state when the catalog request fails', async () => {
    api.popularShows.mockRejectedValueOnce(new Error('offline'))
    const { wrapper } = await render()
    expect(wrapper.text()).toContain('The archive is empty')
    expect(wrapper.text()).toContain('trouble reaching the series catalog')
  })

  it('opens a series from the shelf and closes it through the URL', async () => {
    const { wrapper, router } = await render()
    const trigger = wrapper.get('.result-card')
    await trigger.trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.query.show).toBe('1')
    expect(document.body.querySelector('[role="dialog"]')).not.toBeNull()

    document.body.querySelector('.close-button').click()
    await flushPromises()
    expect(router.currentRoute.value.query.show).toBeUndefined()
    expect(document.body.querySelector('[role="dialog"]')).toBeNull()
    expect(document.activeElement).toBe(trigger.element)
  })
})
