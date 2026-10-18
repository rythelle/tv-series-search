<template>
  <main id="main-content" class="page-shell search-page">
    <section class="search-intro" aria-labelledby="page-title">
      <p class="eyebrow">The series archive · Est. for curious viewers</p>
      <h1 id="page-title">Every story<br /><em>starts somewhere.</em></h1>
      <p class="intro-copy">Find the series you are looking for, then settle in for the details.</p>
      <div class="search-row">
        <div class="search-field">
          <svg aria-hidden="true" viewBox="0 0 24 24" fill="none"><circle cx="10.8" cy="10.8" r="6.8" stroke="currentColor" stroke-width="1.7"/><path d="m16 16 4.5 4.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>
          <label for="search-input" class="visually-hidden">Search TV series</label>
          <input id="search-input" ref="searchInput" v-model="query" type="search" placeholder="Search for a series" autocomplete="off" />
          <span class="search-hint" aria-hidden="true">Find a title</span>
        </div>
        <div class="genre-field">
          <label for="genre-select" class="visually-hidden">Filter by genre</label>
          <select id="genre-select" v-model="genre">
            <option value="">All genres</option>
            <option v-for="name in genres" :key="name" :value="name">{{ name }}</option>
          </select>
          <svg aria-hidden="true" viewBox="0 0 24 24" fill="none"><path d="m6 9.5 6 6 6-6" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>
        </div>
        <button v-if="hasFilters" type="button" class="clear-filters" @click="clearFilters">
          <svg aria-hidden="true" viewBox="0 0 24 24" fill="none"><path d="m7 7 10 10M17 7 7 17" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>
          Clear filters
        </button>
      </div>
    </section>

    <DegradedBanner v-if="degraded" />

    <section class="catalog" aria-labelledby="catalog-title">
      <div class="catalog-heading">
        <div>
          <p class="eyebrow">Now showing</p>
          <h2 id="catalog-title">{{ headingText }}</h2>
        </div>
        <span class="result-count" aria-live="polite">{{ !loading && results.length ? countLabel : '' }}</span>
      </div>
      <ul v-if="loading" class="results" aria-live="polite" aria-busy="true">
        <li v-for="n in 10" :key="n" class="skeleton-card" aria-hidden="true"></li>
      </ul>
      <div v-else-if="results.length === 0" class="empty-state" role="status">
        <h3>{{ query || genre ? 'No matching titles' : 'The archive is empty' }}</h3>
        <p>{{ emptyStateHint }}</p>
      </div>
      <ul v-else class="results">
        <li v-for="show in results" :key="show.id"><ResultCard :show="show" @open="openShow(show.id, $event)" /></li>
        <template v-if="loadingMore">
          <li v-for="n in 5" :key="`more-${n}`" class="skeleton-card" aria-hidden="true"></li>
        </template>
      </ul>
      <div ref="sentinel" class="scroll-sentinel" aria-hidden="true"></div>
      <p class="list-status" :class="{ 'list-status--quiet': !listStatus }" role="status">{{ listStatus }}</p>
    </section>
    <ShowDetailView v-if="selectedShowId" :key="selectedShowId" :id="selectedShowId" @close="closeShow" />
  </main>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api/client'
import DegradedBanner from '../components/DegradedBanner.vue'
import ResultCard from '../components/ResultCard.vue'
import ShowDetailView from './ShowDetailView.vue'

const route = useRoute()
const router = useRouter()
const selectedShowId = computed(() => /^\d+$/.test(String(route.query.show || '')) ? String(route.query.show) : null)
const query = ref('')
const genre = ref('')
const genres = ref([])
const results = ref([])
const total = ref(0)
const nextCursor = ref(null)
const degraded = ref(false)
const loading = ref(false)
const loadingMore = ref(false)
const sentinel = ref(null)
const searchInput = ref(null)
const PAGE_SIZE = 20
let debounceTimer = null
let activeController = null
let triggerElement = null
let observer = null

const headingText = computed(() => {
  if (query.value) return 'Search results'
  return genre.value ? `${genre.value} series` : 'Popular series'
})

// Only the popular listing pages: TVMaze answers a search in a single
// response, so there is no later page to fetch for a query.
//
// The server says whether a next page exists rather than the client comparing
// lengths against `total`, because rows arrive in the middle of the ranking
// while someone is browsing -- every search stores the hits it gets back.
const canLoadMore = computed(() => !query.value && nextCursor.value !== null)
const reachedEnd = computed(
  () => !query.value && !loading.value && results.value.length > 0 && !canLoadMore.value
)
// The archive is a shelf, not a mirror of the whole catalog, so the end of the
// listing is where browsing stops and searching takes over. Saying so beats
// letting the list simply run out.
const listStatus = computed(() => {
  if (loadingMore.value) return 'Loading more titles…'
  if (!reachedEnd.value) return ''
  const shelf = genre.value ? `That is every ${genre.value} title in the archive.` : 'That is every title in the archive.'
  return `${shelf} Search by name to reach titles beyond it.`
})
const countLabel = computed(() =>
  canLoadMore.value ? `${results.value.length} of ${total.value} titles` : `${results.value.length} titles`
)

const hasFilters = computed(() => Boolean(query.value || genre.value))

const emptyStateHint = computed(() => {
  if (query.value && genre.value) return `Nothing in ${genre.value} matches “${query.value}”.`
  if (query.value) return `Try another title or a shorter search for “${query.value}”.`
  if (genre.value) return `No ${genre.value} series in the archive yet.`
  return 'Please try again later.'
})

// Both refs land in the same tick, so the two watchers below collapse into a
// single scheduled fetch -- no need to run one here.
function clearFilters() {
  query.value = ''
  genre.value = ''
  nextTick(() => searchInput.value?.focus())
}

function openShow(id, event) {
  triggerElement = event.currentTarget
  router.push({ name: 'search', query: { ...route.query, show: String(id) } })
}

function closeShow() {
  const nextQuery = { ...route.query }
  delete nextQuery.show
  router.push({ name: 'search', query: nextQuery })
}

async function fetchPage({ append }) {
  if (activeController) activeController.abort()
  const controller = new AbortController()
  activeController = controller
  if (append) loadingMore.value = true
  else loading.value = true
  try {
    const selectedGenre = genre.value || undefined
    const cursor = append ? nextCursor.value : undefined
    const data = query.value
      ? await api.searchShows(query.value, PAGE_SIZE, controller.signal, selectedGenre)
      : await api.popularShows(PAGE_SIZE, controller.signal, selectedGenre, cursor)
    if (controller.signal.aborted) return
    results.value = append ? [...results.value, ...data.items] : data.items
    total.value = data.total ?? data.items.length
    nextCursor.value = data.next_cursor ?? null
    degraded.value = data.degraded
    // Re-observing re-delivers an entry when the sentinel is still on screen,
    // which keeps a viewport taller than one page filling itself.
    nextTick(watchSentinel)
  } catch (err) {
    if (err.name === 'AbortError' || controller.signal.aborted) return
    degraded.value = true
    if (!append) {
      results.value = []
      total.value = 0
      nextCursor.value = null
    }
  } finally {
    if (activeController === controller) {
      loading.value = false
      loadingMore.value = false
    }
  }
}

function runSearch() {
  return fetchPage({ append: false })
}

function loadMore() {
  if (loading.value || loadingMore.value || !canLoadMore.value) return
  fetchPage({ append: true })
}

function watchSentinel() {
  if (!observer || !sentinel.value) return
  observer.unobserve(sentinel.value)
  observer.observe(sentinel.value)
}

async function loadGenres() {
  try {
    genres.value = (await api.genres()).items
  } catch {
    genres.value = []
  }
}

function scheduleSearch(delay) {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(runSearch, delay)
}

watch(query, (value) => scheduleSearch(value ? 300 : 0))
watch(genre, () => scheduleSearch(0))
watch(selectedShowId, (id, previousId) => {
  if (!id && previousId) nextTick(() => triggerElement?.focus())
})
onMounted(() => {
  observer = new IntersectionObserver(
    (entries) => { if (entries.some((entry) => entry.isIntersecting)) loadMore() },
    { rootMargin: '400px' },
  )
  watchSentinel()
  loadGenres()
  runSearch()
})
onUnmounted(() => {
  clearTimeout(debounceTimer)
  activeController?.abort()
  observer?.disconnect()
})
</script>

<style scoped>
.search-page { min-height: calc(100vh - 70px); }
.search-intro { position: relative; padding: clamp(4rem, 8vw, 7rem) 0 4.5rem; max-width: 820px; }
.search-intro::after { content: '01 / ARCHIVE'; position: absolute; right: -20%; top: 24%; color: #645052; font-size: .68rem; letter-spacing: .25em; transform: rotate(90deg); }
.search-intro h1 { margin: 0; color: var(--ink); font-family: Georgia, 'Times New Roman', serif; font-size: clamp(3.5rem, 6.6vw, 6.5rem); line-height: .99; letter-spacing: -.065em; font-weight: 400; }
.search-intro h1 em { color: var(--gold); font-weight: 400; }
.intro-copy { margin: 1.7rem 0 2.2rem; color: var(--muted); font-size: .96rem; line-height: 1.6; }
.search-row { display: flex; flex-wrap: wrap; align-items: center; gap: .9rem; }
.genre-field { position: relative; display: flex; align-items: center; height: 60px; border: 1px solid #79605c; border-radius: 3px; background: #2c2225; transition: border-color .2s; }
.genre-field:focus-within { border-color: var(--gold); }
.genre-field select { appearance: none; height: 100%; min-width: 188px; padding: 0 2.9rem 0 1.1rem; border: 0; outline: 0; background: transparent; color: var(--ink); font-size: .74rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; cursor: pointer; }
.genre-field select option { background: #2c2225; color: var(--ink); letter-spacing: normal; }
.genre-field svg { position: absolute; right: 1rem; width: 18px; color: var(--gold); pointer-events: none; }
.clear-filters { display: inline-flex; align-items: center; gap: .5rem; height: 60px; padding: 0 1.2rem; border: 1px solid #79605c; border-radius: 3px; background: transparent; color: var(--gold); font-family: inherit; font-size: .7rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; cursor: pointer; transition: border-color .2s, color .2s; }
.clear-filters:hover { border-color: var(--gold); color: var(--ink); }
.clear-filters:focus-visible { outline: 2px solid var(--gold); outline-offset: 2px; }
.clear-filters svg { flex: 0 0 16px; width: 16px; }
.search-field { display: flex; align-items: center; gap: .85rem; flex: 1 1 320px; max-width: 620px; height: 60px; padding: 0 1.1rem; border: 1px solid #79605c; border-radius: 3px; background: #2c2225; transition: border-color .2s; }
.search-field:focus-within { border-color: var(--gold); }
.search-field svg { flex: 0 0 21px; width: 21px; color: var(--gold); }
.search-field input { min-width: 0; width: 100%; height: 100%; border: 0; outline: 0; background: transparent; color: var(--ink); font-size: .95rem; }
.search-field input::placeholder { color: #a99b92; }
.search-hint { flex: 0 0 auto; color: var(--gold); font-size: .65rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; }
.catalog { border-top: 1px solid var(--line); padding-top: 2rem; }
.catalog-heading { display: flex; justify-content: space-between; align-items: end; gap: 1rem; margin-bottom: 1.8rem; }
.catalog-heading .eyebrow { margin-bottom: .4rem; }
.catalog-heading h2 { margin: 0; font-family: Georgia, 'Times New Roman', serif; font-size: clamp(1.8rem, 2.7vw, 2.4rem); font-weight: 400; letter-spacing: -.04em; }
.result-count { color: var(--muted); font-size: .72rem; letter-spacing: .15em; text-transform: uppercase; white-space: nowrap; }
.results { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 2.5rem 1.35rem; list-style: none; padding: 0; margin: 0; }
.results li { min-width: 0; }
.skeleton-card { aspect-ratio: 2 / 3.5; background: linear-gradient(100deg, #2b2224 30%, #3a2c2d 45%, #2b2224 60%); background-size: 200% 100%; animation: shimmer 1.6s linear infinite; }
@keyframes shimmer { to { background-position-x: -200%; } }
.scroll-sentinel { height: 1px; }
.list-status { margin: 2.5rem 0 0; color: var(--muted); font-size: .72rem; letter-spacing: .15em; text-transform: uppercase; text-align: center; }
.list-status--quiet { margin: 0; }
.empty-state { padding: 4rem 1rem; text-align: center; border: 1px solid var(--line); background: var(--panel); }
.empty-state h3 { margin: 0 0 .5rem; font-family: Georgia, serif; font-size: 1.4rem; font-weight: 400; }
.empty-state p { margin: 0; color: var(--muted); }
@media (max-width: 1000px) { .results { grid-template-columns: repeat(4, minmax(0, 1fr)); } .search-intro::after { display: none; } }
@media (max-width: 720px) { .results { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1.5rem .85rem; } .search-intro { padding: 3.5rem 0; } }
@media (max-width: 480px) { .results { grid-template-columns: repeat(2, minmax(0, 1fr)); } .search-hint { display: none; } .genre-field { width: 100%; } .genre-field select { width: 100%; } .clear-filters { width: 100%; justify-content: center; } }
@media (prefers-reduced-motion: reduce) { .skeleton-card { animation: none; } }
</style>
