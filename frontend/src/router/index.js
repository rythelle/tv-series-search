import { createRouter, createWebHistory } from 'vue-router'
import SearchView from '../views/SearchView.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'search', component: SearchView },
    { path: '/shows/:id', redirect: (to) => ({ name: 'search', query: { show: to.params.id } }) },
  ],
})
