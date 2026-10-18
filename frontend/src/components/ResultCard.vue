<template>
  <button type="button" class="result-card" :aria-label="`Open details for ${show.name}`" @click="$emit('open', $event)">
    <div class="poster-frame">
      <img v-if="show.poster_url" :src="show.poster_url" :alt="`Poster for ${show.name}`" loading="lazy" />
      <div v-else class="poster-placeholder" aria-hidden="true"><span>{{ show.name }}</span></div>
    </div>
    <div class="card-meta">
      <h3>{{ show.name }}</h3>
      <p><span>{{ show.premiered_year || 'Year unknown' }}</span><span v-if="show.genres?.length" class="meta-divider">·</span><span v-if="show.genres?.length">{{ show.genres.slice(0, 2).join(' / ') }}</span></p>
    </div>
  </button>
</template>

<script setup>
defineProps({ show: { type: Object, required: true } })
defineEmits(['open'])
</script>

<style scoped>
.result-card { display: block; width: 100%; min-width: 0; padding: 0; border: 0; background: transparent; color: inherit; text-align: left; }
.poster-frame { position: relative; width: 100%; aspect-ratio: 2 / 3; overflow: hidden; background: #493136; border: 1px solid #705253; }
.poster-frame::after { content: ''; position: absolute; inset: 0; border: 5px solid transparent; transition: border-color .2s; pointer-events: none; }
.poster-frame img { display: block; width: 100%; height: 100%; object-fit: cover; transition: transform .3s ease; }
.result-card:hover .poster-frame img { transform: scale(1.04); }
.result-card:hover .poster-frame::after, .result-card:focus-visible .poster-frame::after { border-color: var(--gold); }
.poster-placeholder { display: flex; align-items: center; justify-content: center; width: 100%; height: 100%; padding: 1rem; background: #493136; color: var(--gold); text-align: center; font-family: Georgia, serif; font-size: clamp(1rem, 2vw, 1.5rem); line-height: 1.15; }
.card-meta { padding: .8rem .05rem 0; }
.card-meta h3 { margin: 0; color: var(--ink); font-size: .91rem; line-height: 1.3; font-weight: 700; }
.card-meta p { display: flex; flex-wrap: wrap; gap: .35rem; margin: .35rem 0 0; color: var(--muted); font-size: .72rem; line-height: 1.4; }
.meta-divider { color: var(--red); }
@media (prefers-reduced-motion: reduce) { .poster-frame img { transition: none; } }
</style>
