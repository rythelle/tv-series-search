<template>
  <section class="insight-panel">
    <p class="eyebrow">A closer look</p>
    <h3>Insight</h3>
    <p class="panel-intro">A brief perspective on this story.</p>
    <p v-if="checking" class="panel-status" role="status">Checking for an insight…</p>
    <button v-else-if="!insight" type="button" :disabled="loading" @click="generate">{{ loading ? 'Loading…' : 'Show insight' }}</button>
    <p v-if="insight" class="insight-text">{{ insight.text }}</p>
    <p v-if="error" role="alert">{{ error }}</p>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api/client'
const props = defineProps({ targetType: { type: String, required: true }, targetId: { type: [String, Number], required: true } })
const insight = ref(null)
const checking = ref(true)
const loading = ref(false)
const error = ref('')
onMounted(async () => {
  try { insight.value = await api.peekInsight(props.targetType, props.targetId) }
  catch { insight.value = null }
  finally { checking.value = false }
})
async function generate() {
  loading.value = true
  error.value = ''
  try { insight.value = await api.generateInsight(props.targetType, props.targetId) }
  catch { error.value = 'Couldn’t load this insight. Please try again.' }
  finally { loading.value = false }
}
</script>

<style scoped>
.insight-panel { padding: 1.5rem; border: 1px solid #8b6656; background: #37272a; }
.insight-panel .eyebrow { margin-bottom: .5rem; }
.insight-panel h3 { margin: 0; font-family: Georgia, serif; font-size: 1.65rem; font-weight: 400; }
.panel-intro { margin: .5rem 0 1.2rem; color: var(--muted); font-size: .8rem; line-height: 1.5; }
.panel-status { margin: .5rem 0 0; color: var(--muted); font-size: .8rem; }
.insight-panel button { padding: .65rem .9rem; border: 1px solid var(--gold); background: transparent; color: var(--gold); font-size: .7rem; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
.insight-panel button:hover { background: var(--gold); color: var(--bg); }
.insight-panel button:disabled { opacity: .6; cursor: wait; }
.insight-text { margin: 1.2rem 0 0; padding-top: 1rem; border-top: 1px solid #785856; color: var(--ink); font-family: Georgia, serif; font-size: .99rem; line-height: 1.65; }
.insight-panel [role="alert"] { color: #f08a7e; font-size: .8rem; }
</style>
