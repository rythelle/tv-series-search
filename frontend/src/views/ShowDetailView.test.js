import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import ShowDetailView from './ShowDetailView.vue'
import { api } from '../api/client'

vi.mock('../api/client', () => ({
  api: {
    showDetails: vi.fn(), watchedEpisodes: vi.fn(), markWatched: vi.fn(), unmarkWatched: vi.fn(),
    listComments: vi.fn(), postComment: vi.fn(), peekInsight: vi.fn(), generateInsight: vi.fn(),
  },
}))

let wrapper

beforeEach(() => {
  api.showDetails.mockReset().mockResolvedValue({
    show: { id: 7, name: 'Example Series', summary: '<p>A <b>good</b> show.</p>', poster_url: null, genres: ['Drama'], premiered_year: 2020 },
    seasons: [{ number: 1, episodes: [{ id: 101, name: 'Pilot' }] }],
    degraded: false,
  })
  api.watchedEpisodes.mockReset().mockResolvedValue({ episode_ids: [101] })
  api.markWatched.mockReset().mockResolvedValue(null)
  api.unmarkWatched.mockReset().mockResolvedValue(null)
  api.listComments.mockReset().mockResolvedValue({ items: [] })
  api.peekInsight.mockReset().mockResolvedValue(null)
  api.generateInsight.mockReset().mockResolvedValue({ text: 'A thoughtful story.' })
})

afterEach(() => {
  wrapper?.unmount()
  wrapper = null
  document.body.innerHTML = ''
  expect(document.body.style.overflow).toBe('')
})

async function render() {
  wrapper = mount(ShowDetailView, { props: { id: 7 }, attachTo: document.body, global: { plugins: [createPinia()] } })
  await flushPromises()
  return wrapper
}

describe('series details', () => {
  it('shows seasons, watched progress, safe summary, and closes with Escape', async () => {
    const view = await render()
    expect(document.body.textContent).toContain('Example Series')
    expect(document.body.textContent).toContain('A good show.')
    expect(document.body.querySelector('.show-summary b')).toBeNull()
    expect(document.body.textContent).toContain('1/1 watched')
    expect(document.body.querySelector('.episode-label input').checked).toBe(true)
    expect(document.activeElement).toBe(document.body.querySelector('.close-button'))

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    expect(view.emitted('close')).toHaveLength(1)
  })

  it('rolls back an optimistic watched change when saving fails', async () => {
    api.unmarkWatched.mockRejectedValueOnce(new Error('offline'))
    await render()
    const checkbox = document.body.querySelector('.episode-label input')

    checkbox.checked = false
    checkbox.dispatchEvent(new Event('change', { bubbles: true }))
    await flushPromises()

    expect(checkbox.checked).toBe(true)
    expect(document.body.textContent).toContain("Couldn't save — try again.")
    expect(document.body.textContent).toContain('1/1 watched')
  })

  it('shows a retry message when details cannot load', async () => {
    api.showDetails.mockRejectedValueOnce(new Error('offline'))
    await render()
    expect(document.body.querySelector('[role="alert"]').textContent).toContain('could not be loaded')
  })
})
