import { createRouter, createWebHistory } from 'vue-router'
import BasicLayout from '../layouts/BasicLayout.vue'
import LoginPage from '../pages/LoginPage.vue'
import MessagesPage from '../pages/MessagesPage.vue'
import ContactsPage from '../pages/ContactsPage.vue'
import AgentCenterPage from '../pages/AgentCenterPage.vue'
import AgentDetailPage from '../pages/AgentDetailPage.vue'
import AgentProfileDetailPage from '../pages/AgentProfileDetailPage.vue'
import AdminUsersPage from '../pages/AdminUsersPage.vue'
import ProfilePage from '../pages/ProfilePage.vue'
import ProjectCodePage from '../pages/ProjectCodePage.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/login', name: 'login', component: LoginPage },
    {
      path: '/',
      component: BasicLayout,
      meta: { requiresAuth: true },
      children: [
        { path: '', redirect: '/messages' },
        { path: 'messages', name: 'messages', component: MessagesPage, meta: { requiresAuth: true } },
        { path: 'profile', name: 'profile', component: ProfilePage, meta: { requiresAuth: true } },
        { path: 'contacts', name: 'contacts', component: ContactsPage, meta: { requiresAuth: true } },
        { path: 'project-code', name: 'project-code', component: ProjectCodePage, meta: { requiresAuth: true } },
        { path: 'agents', name: 'agents', component: AgentCenterPage, meta: { requiresAuth: true } },
        { path: 'agents/:id', name: 'agent-detail', component: AgentDetailPage, meta: { requiresAuth: true } },
        { path: 'agent-profiles/:id', name: 'agent-profile-detail', component: AgentProfileDetailPage, meta: { requiresAuth: true } },
        { path: 'admin/users', name: 'admin-users', component: AdminUsersPage, meta: { requiresAuth: true } },
      ],
    },
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
