import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import CommentSection from './CommentSection.vue'
import InsightPanel from './InsightPanel.vue'
import { api } from '../api/client'

vi.mock('../api/client', () => ({
  api: { listComments: vi.fn(), postComment: vi.fn(), peekInsight: vi.fn(), generateInsight: vi.fn() },
}))

let wrapper

beforeEach(() => {
  localStorage.setItem('tv-series-search:viewer-id', 'viewer-1')
  api.listComments.mockReset().mockResolvedValue({ items: [{ id: 1, body: 'First thought', viewer_id: 'viewer-1' }] })
  api.postComment.mockReset().mockResolvedValue({ id: 2, body: 'New thought', viewer_id: 'viewer-1' })
  api.peekInsight.mockReset().mockResolvedValue(null)
  api.generateInsight.mockReset().mockResolvedValue({ text: 'An insightful sentence.' })
})

afterEach(() => {
  wrapper?.unmount()
  wrapper = null
  localStorage.clear()
})

async function render(component) {
  wrapper = mount(component, { props: { targetType: 'show', targetId: 7 }, global: { plugins: [createPinia()] } })
  await flushPromises()
  return wrapper
}

describe('comments', () => {
  it('shows existing comments and adds a submitted comment to the list', async () => {
    const view = await render(CommentSection)
    expect(view.text()).toContain('First thought')
    expect(view.text()).toContain('You')

    await view.get('textarea').setValue('New thought')
    await view.get('form').trigger('submit')
    await flushPromises()

    expect(view.findAll('li').map((item) => item.text())).toEqual(['New thoughtYou', 'First thoughtYou'])
    expect(view.get('textarea').element.value).toBe('')
  })

  it('keeps the draft and shows an error when posting fails', async () => {
    api.postComment.mockRejectedValueOnce(new Error('offline'))
    const view = await render(CommentSection)
    await view.get('textarea').setValue('Keep this')
    await view.get('form').trigger('submit')
    await flushPromises()

    expect(view.get('textarea').element.value).toBe('Keep this')
    expect(view.get('[role="alert"]').text()).toContain('Couldn’t post')
  })
})

describe('insights', () => {
  it('shows a cached insight without asking the user to generate it', async () => {
    api.peekInsight.mockResolvedValueOnce({ text: 'Already here.' })
    const view = await render(InsightPanel)
    expect(view.text()).toContain('Already here.')
    expect(view.find('button').exists()).toBe(false)
  })

  it('generates an insight on demand', async () => {
    const view = await render(InsightPanel)
    await view.get('button').trigger('click')
    await flushPromises()

    expect(view.text()).toContain('An insightful sentence.')
    expect(view.find('button').exists()).toBe(false)
  })

  it('offers a retry when insight generation fails', async () => {
    api.generateInsight.mockRejectedValueOnce(new Error('offline'))
    const view = await render(InsightPanel)
    await view.get('button').trigger('click')
    await flushPromises()

    expect(view.get('[role="alert"]').text()).toContain('try again')
    expect(view.get('button').text()).toBe('Show insight')
  })
})
