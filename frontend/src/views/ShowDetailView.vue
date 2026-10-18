<template>
  <Teleport to="body">
    <div class="modal-backdrop" @click.self="emit('close')">
      <section ref="dialog" class="show-modal" role="dialog" aria-modal="true" aria-label="Series details" tabindex="-1">
        <div class="modal-topline"><span>TV Series Search / The archive</span><button ref="closeButton" type="button" class="close-button" aria-label="Close series details" @click="emit('close')">×</button></div>
        <p v-if="loading" class="detail-loading" role="status">Loading series…</p>
        <template v-else-if="show">
          <DegradedBanner v-if="degraded" />
          <div class="show-hero">
            <div class="detail-poster">
              <img v-if="show.poster_url" :src="show.poster_url" :alt="`Poster for ${show.name}`" />
              <div v-else class="detail-poster-placeholder" aria-hidden="true">{{ show.name }}</div>
            </div>
            <div class="show-overview">
              <p class="eyebrow">Feature presentation</p>
              <h2>{{ show.name }}</h2>
              <p v-if="show.premiered_year" class="show-year">{{ show.premiered_year }}</p>
              <ul v-if="show.genres?.length" class="genres"><li v-for="genre in show.genres" :key="genre">{{ genre }}</li></ul>
              <p v-if="plainSummary" class="show-summary">{{ plainSummary }}</p>
            </div>
          </div>
          <div class="detail-layout">
            <div class="detail-primary">
              <div class="section-heading"><p class="eyebrow">Episode guide</p><h3>Seasons</h3></div>
              <p v-if="!seasons.length" class="muted">{{ degraded ? 'Episodes are temporarily unavailable. Please try again later.' : 'No episodes are listed for this series.' }}</p>
              <section v-for="season in seasons" :key="season.number" class="season">
                <button class="season-toggle" type="button" :aria-expanded="isOpen(season.number)" @click="toggleSeason(season.number)">
                  <span>{{ season.number === 0 ? 'Specials' : `Season ${season.number}` }}</span>
                  <span class="season-count">{{ watchedCount(season) }}/{{ season.episodes.length }} watched <span class="chevron" :class="{ open: isOpen(season.number) }">⌄</span></span>
                </button>
                <ul v-show="isOpen(season.number)" class="episode-list">
                  <li v-for="episode in season.episodes" :key="episode.id" class="episode">
                    <div class="episode-line">
                      <label class="episode-label"><input type="checkbox" :checked="viewer.isWatched(episode.id)" @change="toggleWatched(episode.id, $event.target.checked)" /><span>{{ episode.name }}</span></label>
                      <div class="episode-actions">
                        <button class="text-button" type="button" @click="toggleEpisodeInsight(episode.id)">{{ openEpisodeInsights.has(episode.id) ? 'Hide insight' : 'Insight' }}</button>
                        <button class="text-button" type="button" @click="toggleEpisodeComments(episode.id)">{{ openEpisodeComments.has(episode.id) ? 'Hide comments' : 'Comments' }}</button>
                      </div>
                    </div>
                    <span v-if="errorEpisodeId === episode.id" class="inline-error" role="alert">Couldn't save — try again.</span>
                    <InsightPanel v-if="openEpisodeInsights.has(episode.id)" class="episode-insight" target-type="episode" :target-id="episode.id" />
                    <CommentSection v-if="openEpisodeComments.has(episode.id)" target-type="episode" :target-id="episode.id" />
                  </li>
                </ul>
              </section>
            </div>
            <aside class="detail-aside" aria-label="More about this series">
              <InsightPanel target-type="show" :target-id="show.id" />
              <CommentSection target-type="show" :target-id="show.id" />
            </aside>
          </div>
        </template>
        <div v-else class="detail-loading" role="alert">This series could not be loaded. Please try again.</div>
      </section>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { api } from '../api/client'
import { useViewerStore } from '../stores/viewer'
import CommentSection from '../components/CommentSection.vue'
import DegradedBanner from '../components/DegradedBanner.vue'
import InsightPanel from '../components/InsightPanel.vue'

const props = defineProps({ id: { type: [String, Number], required: true } })
const emit = defineEmits(['close'])
const viewer = useViewerStore()
const dialog = ref(null)
const closeButton = ref(null)
const loading = ref(true)
const show = ref(null)
const seasons = ref([])
const degraded = ref(false)
const openSeasons = ref(new Set())
const openEpisodeComments = ref(new Set())
const openEpisodeInsights = ref(new Set())
const errorEpisodeId = ref(null)
const plainSummary = computed(() => show.value ? (show.value.summary || '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim() : '')
let previousOverflow = ''

function handleKeydown(event) {
  if (event.key === 'Escape') { emit('close'); return }
  if (event.key !== 'Tab' || !dialog.value) return
  const focusable = [...dialog.value.querySelectorAll('button:not(:disabled), input:not(:disabled), textarea:not(:disabled), a[href]')]
  if (!focusable.length) return
  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
}
function isOpen(number) { return openSeasons.value.has(number) }
function toggleSeason(number) { const next = new Set(openSeasons.value); next.has(number) ? next.delete(number) : next.add(number); openSeasons.value = next }
function toggleEpisodeComments(id) { const next = new Set(openEpisodeComments.value); next.has(id) ? next.delete(id) : next.add(id); openEpisodeComments.value = next }
function toggleEpisodeInsight(id) { const next = new Set(openEpisodeInsights.value); next.has(id) ? next.delete(id) : next.add(id); openEpisodeInsights.value = next }
function watchedCount(season) { return season.episodes.filter((episode) => viewer.isWatched(episode.id)).length }

async function toggleWatched(episodeId, watched) {
  if (watched) viewer.markWatched(episodeId)
  else viewer.unmarkWatched(episodeId)
  try {
    if (watched) await api.markWatched(episodeId)
    else await api.unmarkWatched(episodeId)
    errorEpisodeId.value = null
  } catch {
    if (watched) viewer.unmarkWatched(episodeId)
    else viewer.markWatched(episodeId)
    errorEpisodeId.value = episodeId
  }
}

onMounted(async () => {
  previousOverflow = document.body.style.overflow
  document.body.style.overflow = 'hidden'
  window.addEventListener('keydown', handleKeydown)
  await nextTick()
  closeButton.value?.focus()
  try {
    const details = await api.showDetails(props.id)
    show.value = details.show
    seasons.value = details.seasons || []
    degraded.value = details.degraded
    openSeasons.value = new Set(seasons.value.slice(0, 1).map((season) => season.number))
  } catch {
    show.value = null
  } finally {
    loading.value = false
  }
  if (show.value) {
    try { const watched = await api.watchedEpisodes(props.id); viewer.setWatched(watched.episode_ids) }
    catch { viewer.setWatched([]) }
  }
})
onUnmounted(() => { document.body.style.overflow = previousOverflow; window.removeEventListener('keydown', handleKeydown) })
</script>

<style scoped>
.modal-backdrop { position: fixed; inset: 0; z-index: 50; display: flex; align-items: center; justify-content: center; padding: 1rem; background: rgba(8, 6, 8, .82); backdrop-filter: blur(5px); }
.show-modal { width: min(1120px, 100%); max-height: calc(100dvh - 2rem); overflow-y: auto; overscroll-behavior: contain; border: 1px solid #75564f; background: #211a1d; box-shadow: 0 25px 80px rgba(0, 0, 0, .55); outline: none; }
.modal-topline { position: sticky; top: 0; z-index: 2; display: flex; align-items: center; justify-content: space-between; min-height: 48px; padding: 0 1rem 0 2rem; border-bottom: 1px solid var(--line); background: #211a1d; color: var(--gold); font-size: .63rem; font-weight: 700; letter-spacing: .2em; text-transform: uppercase; }
.close-button { width: 42px; height: 42px; border: 0; background: transparent; color: var(--ink); font-size: 2rem; line-height: 1; }
.close-button:hover { color: var(--gold); }
.detail-loading { padding: 5rem 2rem; color: var(--muted); }
.show-hero { display: grid; grid-template-columns: minmax(160px, 245px) minmax(0, 1fr); gap: clamp(2rem, 5vw, 4rem); align-items: center; padding: clamp(1.5rem, 4vw, 3rem); }
.detail-poster { width: 100%; aspect-ratio: 2 / 3; overflow: hidden; border: 1px solid #8c665a; background: #493136; box-shadow: 10px 10px 0 #34272a; }
.detail-poster img { display: block; width: 100%; height: 100%; object-fit: cover; }
.detail-poster-placeholder { display: grid; place-items: center; width: 100%; height: 100%; padding: 1.5rem; text-align: center; color: var(--gold); font-family: Georgia, serif; font-size: 1.5rem; }
.show-overview h2 { margin: 0; font-family: Georgia, 'Times New Roman', serif; font-size: clamp(2.5rem, 5vw, 4.6rem); line-height: 1.02; font-weight: 400; letter-spacing: -.05em; }
.show-year { margin: 1rem 0 0; color: var(--gold); font-size: .8rem; letter-spacing: .16em; }
.genres { display: flex; flex-wrap: wrap; gap: .5rem; list-style: none; padding: 0; margin: 1.5rem 0; }
.genres li { padding: .4rem .7rem; border: 1px solid #8b6a5a; color: var(--ink); font-size: .7rem; letter-spacing: .08em; text-transform: uppercase; }
.show-summary { max-width: 62ch; margin: 1.4rem 0 0; color: #cfc2b4; font-size: .9rem; line-height: 1.75; }
.detail-layout { display: grid; grid-template-columns: minmax(0, 1fr) minmax(250px, 300px); gap: clamp(1.5rem, 4vw, 3rem); padding: 2.5rem clamp(1.5rem, 4vw, 3rem) 3rem; border-top: 1px solid var(--line); }
.section-heading { margin-bottom: 1.5rem; }
.section-heading .eyebrow { margin-bottom: .4rem; }
.section-heading h3 { margin: 0; font-family: Georgia, serif; font-size: 2rem; font-weight: 400; }
.season { border-top: 1px solid var(--line); }
.season:last-child { border-bottom: 1px solid var(--line); }
.season-toggle { display: flex; justify-content: space-between; align-items: center; gap: 1rem; width: 100%; padding: 1.1rem 0; border: 0; background: transparent; color: var(--ink); text-align: left; font-weight: 700; }
.season-toggle > span:first-child { min-width: 0; overflow-wrap: anywhere; }
.season-count { color: var(--muted); font-size: .72rem; font-weight: 400; white-space: nowrap; }
.chevron { display: inline-block; margin-left: .6rem; color: var(--gold); font-size: 1.2rem; line-height: .5; transition: transform .2s; }
.chevron.open { transform: rotate(180deg); }
.episode-list { list-style: none; padding: 0 0 .5rem; margin: 0; }
.episode { padding: .8rem 0; border-top: 1px solid #47383a; }
.episode-line { display: flex; justify-content: space-between; align-items: center; gap: 1rem; }
.episode-label { display: flex; align-items: center; gap: .75rem; min-width: 0; overflow-wrap: anywhere; font-size: .84rem; }
.episode-label input { flex: 0 0 auto; accent-color: var(--red); width: 1rem; height: 1rem; }
.episode-actions { flex: 0 0 auto; display: flex; gap: 1rem; }
.text-button { flex: 0 0 auto; border: 0; background: transparent; color: var(--gold); font-size: .73rem; }
.text-button:hover { text-decoration: underline; }
.episode-insight { margin-top: .8rem; }
.inline-error { display: block; margin: .5rem 0 0 1.75rem; color: #f08a7e; font-size: .77rem; }
.detail-aside { display: flex; flex-direction: column; gap: 1.2rem; }
@media (max-width: 800px) { .detail-layout { grid-template-columns: 1fr; } .detail-aside { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 600px) { .modal-backdrop { padding: 0; } .show-modal { max-height: 100dvh; min-height: 100dvh; } .show-hero { grid-template-columns: 100px minmax(0, 1fr); gap: 1.2rem; align-items: start; } .show-overview h2 { font-size: clamp(2rem, 8vw, 3rem); } .show-summary { font-size: .82rem; } .detail-aside { grid-template-columns: 1fr; } .episode-line { align-items: start; } }
@media (prefers-reduced-motion: reduce) { .chevron { transition: none; } }
</style>
