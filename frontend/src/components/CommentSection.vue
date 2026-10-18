<template>
  <section class="comments">
    <p class="eyebrow">After the credits</p>
    <h3>Comments</h3>
    <p v-if="!comments.length && !error" class="comments-empty">Be the first to share a thought.</p>
    <ul aria-live="polite">
      <li v-for="comment in comments" :key="comment.id">
        <p>{{ comment.body }}</p>
        <small v-if="comment.viewer_id === viewer.viewerId">You</small>
      </li>
    </ul>
    <form @submit.prevent="submit">
      <label :for="inputId">Add a comment</label>
      <textarea :id="inputId" v-model="draft" maxlength="1000" placeholder="What did you think?"></textarea>
      <button type="submit" :disabled="submitting || !draft.trim()">{{ submitting ? 'Posting…' : 'Post comment' }}</button>
      <p v-if="error" role="alert">{{ error }}</p>
    </form>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api/client'
import { useViewerStore } from '../stores/viewer'
const props = defineProps({ targetType: { type: String, required: true }, targetId: { type: [String, Number], required: true } })
const viewer = useViewerStore()
const comments = ref([])
const draft = ref('')
const submitting = ref(false)
const error = ref('')
const inputId = `comment-${props.targetType}-${props.targetId}`
async function load() {
  try { const response = await api.listComments(props.targetType, props.targetId); comments.value = response.items }
  catch { error.value = 'Comments are unavailable right now.' }
}
async function submit() {
  submitting.value = true
  error.value = ''
  try {
    const created = await api.postComment(props.targetType, props.targetId, draft.value)
    comments.value = [created, ...comments.value]
    draft.value = ''
  } catch { error.value = 'Couldn’t post your comment. Please try again.' }
  finally { submitting.value = false }
}
onMounted(load)
</script>

<style scoped>
.comments { padding: 1.5rem; border: 1px solid var(--line); background: #2a2023; }
.comments .eyebrow { margin-bottom: .5rem; }
.comments h3 { margin: 0 0 1rem; font-family: Georgia, serif; font-size: 1.65rem; font-weight: 400; }
.comments-empty { margin: 0 0 1.2rem; color: var(--muted); font-size: .8rem; }
.comments ul { list-style: none; padding: 0; margin: 0 0 1.3rem; }
.comments li { padding: .85rem 0; border-top: 1px solid var(--line); }
.comments li p { margin: 0; color: var(--ink); font-size: .84rem; line-height: 1.55; overflow-wrap: anywhere; }
.comments li small { display: block; margin-top: .35rem; color: var(--gold); font-size: .67rem; letter-spacing: .1em; text-transform: uppercase; }
.comments form { display: grid; gap: .65rem; }
.comments label { color: var(--gold); font-size: .69rem; font-weight: 800; letter-spacing: .13em; text-transform: uppercase; }
.comments textarea { width: 100%; min-height: 90px; resize: vertical; padding: .8rem; border: 1px solid #80605d; border-radius: 0; background: #1b1518; color: var(--ink); font-size: .82rem; }
.comments textarea::placeholder { color: #9f8f87; }
.comments button { justify-self: start; padding: .7rem 1rem; border: 0; background: var(--red); color: #fff0de; font-size: .7rem; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }
.comments button:hover { background: #ca6254; }
.comments button:disabled { opacity: .5; cursor: not-allowed; }
.comments [role="alert"] { margin: 0; color: #f08a7e; font-size: .77rem; }
</style>
