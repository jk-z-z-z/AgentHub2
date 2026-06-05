<template>
  <ContactDirectory
    v-model:search-keyword="searchKeyword"
    v-model:detail-open="detailOpen"
    :loading="loading"
    :list-error="listError"
    :visible-users="visibleUsers"
    :selected-user="selectedUser"
    :current-user-id="currentUserId"
    :contacting="contacting"
    @load-contacts="loadContacts"
    @select-user="selectUser"
    @contact-now="contactNow"
  />
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { apiCreateGroup } from '../api/groups'
import { apiGetCurrentUser, apiListUsers, type User } from '../api/users'
import ContactDirectory from '../components/contacts/ContactDirectory.vue'

const router = useRouter()

const loading = ref(false)
const contacting = ref(false)
const listError = ref('')
const searchKeyword = ref('')
const users = ref<User[]>([])
const selectedUserId = ref('')
const currentUserId = ref('')
const detailOpen = ref(false)

const contactUsers = computed(() => users.value.filter((user) => user.id !== currentUserId.value))

const visibleUsers = computed(() => {
  const query = searchKeyword.value.trim().toLowerCase()
  if (!query) return contactUsers.value
  return contactUsers.value.filter((user) => {
    const haystack = [
      user.username,
      user.email,
      user.display_name || '',
      user.role,
      user.status,
      user.bio || '',
    ]
      .join(' ')
      .toLowerCase()
    return haystack.includes(query)
  })
})

const selectedUser = computed(
  () => users.value.find((user) => user.id === selectedUserId.value) || null,
)

function displayName(user: User) {
  return user.display_name || user.username || user.email || '未命名联系人'
}

function selectUser(userId: string) {
  selectedUserId.value = userId
  detailOpen.value = false
}

async function loadContacts() {
  loading.value = true
  listError.value = ''
  try {
    const [usersResult, currentUserResult] = await Promise.allSettled([
      apiListUsers(),
      apiGetCurrentUser(),
    ])

    if (usersResult.status === 'fulfilled') {
      users.value = usersResult.value.data
    }

    if (currentUserResult.status === 'fulfilled') {
      currentUserId.value = currentUserResult.value.data.id
    }

    const firstVisible = visibleUsers.value[0]
    if (!selectedUserId.value || !users.value.some((user) => user.id === selectedUserId.value)) {
      selectedUserId.value = firstVisible?.id || ''
    }
  } catch (error) {
    listError.value = error instanceof Error ? error.message : String(error)
  } finally {
    loading.value = false
  }
}

async function contactNow() {
  if (!selectedUser.value || selectedUser.value.id === currentUserId.value) return
  contacting.value = true
  try {
    const result = await apiCreateGroup({
      name: `与${displayName(selectedUser.value)}的单聊`,
      description: null,
      type: 'personal',
      users: [
        {
          user_id: selectedUser.value.id,
          display_name: displayName(selectedUser.value),
          title: null,
        },
      ],
      agents: [],
    })
    await router.push({ name: 'messages', query: { groupId: result.data.id } })
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : String(error))
  } finally {
    contacting.value = false
  }
}

onMounted(loadContacts)
</script>

<style scoped>
.searchBar :deep() {
  height: 38px;
  border-radius: 12px;
  box-shadow: none;
  background: rgba(31, 35, 41, 0.04);
}

.searchBar :deep() {
  box-shadow: 0 0 0 1px rgba(79, 140, 255, 0.35) inset;
}

.drawerRow span:first-child {
  color: rgba(31, 35, 41, 0.48);
  flex: 0 0 auto;
}
</style>
