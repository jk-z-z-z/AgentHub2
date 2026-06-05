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
    const haystack = [user.username, user.email, user.display_name || '', user.role, user.status, user.bio || '']
      .join(' ')
      .toLowerCase()
    return haystack.includes(query)
  })
})

const selectedUser = computed(() => users.value.find((user) => user.id === selectedUserId.value) || null)

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
    const [usersResult, currentUserResult] = await Promise.allSettled([apiListUsers(), apiGetCurrentUser()])

    if (usersResult.status === 'fulfilled') {
      users.value = usersResult.value.data
    } else {
      throw usersResult.reason
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
.contactsPage {
  height: calc(100vh - 36px);
  display: grid;
  grid-template-columns: 340px minmax(0, 1fr);
  gap: 12px;
  min-width: 0;
}

.contactsListPanel,
.detailPanel {
  min-width: 0;
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 18px;
  backdrop-filter: blur(10px);
  overflow: hidden;
}

.contactsListPanel {
  display: flex;
  flex-direction: column;
  padding: 16px;
}

.panelHeader {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.eyebrow {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(31, 35, 41, 0.48);
}

.panelTitle {
  margin-top: 4px;
  font-size: 22px;
  line-height: 1.2;
  font-weight: 900;
  color: rgba(31, 35, 41, 0.96);
}

.panelSub {
  margin-top: 6px;
  font-size: 12px;
  color: rgba(31, 35, 41, 0.56);
}

.countPill {
  flex: 0 0 auto;
  height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(79, 140, 255, 0.1);
  color: #2563eb;
  font-size: 12px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
}

.searchBar {
  margin-bottom: 14px;
}

.searchBar :deep(.el-input__wrapper) {
  height: 38px;
  border-radius: 12px;
  box-shadow: none;
  background: rgba(31, 35, 41, 0.04);
}

.searchBar :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px rgba(79, 140, 255, 0.35) inset;
}

.searchIcon {
  color: rgba(31, 35, 41, 0.42);
}

.sectionTitle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  font-size: 13px;
  font-weight: 800;
  color: rgba(31, 35, 41, 0.84);
}

.sectionHint {
  color: rgba(31, 35, 41, 0.46);
  font-weight: 600;
}

.stateBlock {
  padding: 12px 4px 4px;
}

.stateError {
  display: grid;
  gap: 10px;
}

.stateTitle {
  font-size: 14px;
  font-weight: 800;
  color: rgba(31, 35, 41, 0.9);
}

.stateText {
  font-size: 13px;
  line-height: 1.6;
  color: rgba(31, 35, 41, 0.58);
  word-break: break-all;
}

.stateAction {
  justify-self: start;
}

.contactList {
  display: grid;
  gap: 8px;
  overflow: auto;
  padding-right: 2px;
}

.contactRow {
  width: 100%;
  border: 0;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.7);
  padding: 12px 12px 12px 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 12px;
  text-align: left;
  color: inherit;
  transition:
    background 0.14s ease,
    transform 0.14s ease,
    box-shadow 0.14s ease;
}

.contactRow:hover {
  background: rgba(79, 140, 255, 0.08);
  transform: translateY(-1px);
}

.contactRow.active {
  background: linear-gradient(135deg, rgba(79, 140, 255, 0.14), rgba(79, 140, 255, 0.06));
  box-shadow: inset 0 0 0 1px rgba(79, 140, 255, 0.18);
}

.contactRow.self {
  opacity: 0.9;
}

.avatar,
.detailAvatar {
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: linear-gradient(135deg, #4f8cff, #78a7ff);
  color: #fff;
  font-weight: 900;
}

.avatar {
  width: 40px;
  height: 40px;
  font-size: 15px;
}

.contactMeta {
  min-width: 0;
  flex: 1;
}

.contactTop,
.contactBottom,
.detailNameRow {
  display: flex;
  align-items: center;
  gap: 8px;
}

.contactTop {
  justify-content: space-between;
}

.contactName,
.detailName {
  font-size: 14px;
  font-weight: 800;
  color: rgba(31, 35, 41, 0.94);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tag,
.heroTag {
  flex: 0 0 auto;
  height: 20px;
  padding: 0 8px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 800;
  background: rgba(31, 35, 41, 0.06);
  color: rgba(31, 35, 41, 0.62);
}

.contactBottom {
  margin-top: 4px;
  font-size: 12px;
  color: rgba(31, 35, 41, 0.52);
  flex-wrap: wrap;
}

.contactLine {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dot {
  color: rgba(31, 35, 41, 0.36);
}

.detailPanel {
  padding: 18px;
}

.detailCard {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow: auto;
}

.detailHero {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 18px;
  border-radius: 20px;
  background:
    radial-gradient(circle at top right, rgba(79, 140, 255, 0.16), transparent 34%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(246, 249, 255, 0.88));
  border: 1px solid rgba(31, 35, 41, 0.08);
}

.detailAvatar {
  width: 72px;
  height: 72px;
  font-size: 28px;
}

.detailHeroMeta {
  min-width: 0;
  flex: 1;
}

.detailUser,
.detailEmail {
  margin-top: 6px;
  font-size: 13px;
  color: rgba(31, 35, 41, 0.58);
  word-break: break-all;
}

.detailArrowBtn {
  width: 42px;
  height: 42px;
  border: 0;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.88);
  color: rgba(31, 35, 41, 0.78);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: inset 0 0 0 1px rgba(31, 35, 41, 0.08);
}

.detailArrowBtn:hover {
  background: rgba(79, 140, 255, 0.1);
  color: #2563eb;
}

.detailSection {
  padding: 18px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(31, 35, 41, 0.08);
}

.detailSectionTitle {
  font-size: 14px;
  font-weight: 900;
  color: rgba(31, 35, 41, 0.9);
  margin-bottom: 12px;
}

.detailGrid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.kv {
  padding: 12px;
  border-radius: 14px;
  background: rgba(31, 35, 41, 0.03);
}

.k {
  font-size: 12px;
  color: rgba(31, 35, 41, 0.48);
}

.v {
  margin-top: 6px;
  font-size: 13px;
  line-height: 1.5;
  color: rgba(31, 35, 41, 0.9);
  word-break: break-all;
}

.bioBox {
  min-height: 120px;
  padding: 14px;
  border-radius: 16px;
  background: rgba(31, 35, 41, 0.03);
  color: rgba(31, 35, 41, 0.82);
  line-height: 1.8;
  white-space: pre-wrap;
}

.detailFooter {
  margin-top: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.detailTip {
  font-size: 12px;
  color: rgba(31, 35, 41, 0.54);
  line-height: 1.6;
}

.contactBtn {
  min-width: 132px;
  height: 42px;
  border-radius: 14px;
}

.emptyPanel {
  height: 100%;
  display: grid;
  place-items: center;
}

.drawerHero {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(31, 35, 41, 0.08);
}

.drawerAvatar {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #4f8cff, #78a7ff);
  color: #fff;
  font-weight: 900;
  font-size: 20px;
}

.drawerMeta {
  min-width: 0;
  flex: 1;
}

.drawerName {
  font-size: 16px;
  font-weight: 900;
  color: rgba(31, 35, 41, 0.94);
}

.drawerSub {
  margin-top: 6px;
  font-size: 12px;
  color: rgba(31, 35, 41, 0.54);
  word-break: break-all;
}

.drawerSection {
  margin-top: 16px;
}

.drawerTitle {
  font-size: 13px;
  font-weight: 800;
  color: rgba(31, 35, 41, 0.78);
  margin-bottom: 10px;
}

.drawerRows {
  display: grid;
  gap: 8px;
}

.drawerRow {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(31, 35, 41, 0.03);
  font-size: 13px;
  color: rgba(31, 35, 41, 0.82);
  word-break: break-all;
}

.drawerRow span:first-child {
  color: rgba(31, 35, 41, 0.48);
  flex: 0 0 auto;
}

.drawerBio {
  padding: 12px;
  border-radius: 12px;
  background: rgba(31, 35, 41, 0.03);
  color: rgba(31, 35, 41, 0.82);
  line-height: 1.7;
  white-space: pre-wrap;
}

@media (max-width: 1200px) {
  .contactsPage {
    grid-template-columns: 300px minmax(0, 1fr);
  }
}

@media (max-width: 960px) {
  .contactsPage {
    grid-template-columns: 1fr;
    height: auto;
  }

  .detailPanel {
    min-height: 520px;
  }
}
</style>
