import { createRouter, createWebHistory } from 'vue-router'
import MessagesPage from '@/pages/MessagesPage.vue'
import LoginPage from '@/pages/LoginPage.vue'
import MembersPage from '@/pages/MembersPage.vue'
import AgentsPage from '@/pages/AgentsPage.vue'
import AgentDetailPage from '@/pages/AgentDetailPage.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/login', name: 'login', component: LoginPage },
    { path: '/', name: 'messages', component: MessagesPage, meta: { requiresAuth: true } },
    { path: '/contacts', name: 'contacts', component: MembersPage, meta: { requiresAuth: true } },
    { path: '/members', redirect: { name: 'contacts' } },
    { path: '/agents', name: 'agents', component: AgentsPage, meta: { requiresAuth: true } },
    { path: '/agents/:id', name: 'agent-detail', component: AgentDetailPage, meta: { requiresAuth: true } },
  ],
})

router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) {
    return { name: 'login' }
  }
  if (to.name === 'login' && token) {
    return { name: 'messages' }
  }
  return true
})

export default router
