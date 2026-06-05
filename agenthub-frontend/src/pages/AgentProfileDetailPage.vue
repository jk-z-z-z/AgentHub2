<template>
  <AgentProfileWorkspace
    :profile-id="profileId"
    :profile="profile"
    :files="files"
    :toggles="toggles"
    :active-file="activeFile"
    :loading="loading"
    :saving="saving"
    :saving-toggles="savingToggles"
    :err="err"
    v-model:content="content"
    @back="router.push('/agents')"
    @reload-all="reloadAll"
    @open-file="openFile"
    @save-active="saveActive"
    @save-toggles="saveToggles"
  />
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  apiGetAgentProfileFile,
  apiGetAgentProfileFileToggles,
  apiListAgentProfileFiles,
  apiListAgentProfiles,
  apiUpdateAgentProfileFile,
  apiUpdateAgentProfileFileToggles,
  type AgentProfile,
} from '../api/agents'
import AgentProfileWorkspace from '../components/agents/AgentProfileWorkspace.vue'

const route = useRoute()
const router = useRouter()

const profileId = computed(() => String(route.params.id || ''))
const profile = ref<AgentProfile | null>(null)

const files = ref<string[]>([])
const toggles = ref<Record<string, boolean>>({})

const activeFile = ref('')
const content = ref('')
const loading = ref(false)
const saving = ref(false)
const savingToggles = ref(false)
const err = ref('')

async function loadProfileMeta() {
  const res = await apiListAgentProfiles()
  profile.value = res.data.find((p) => String(p.id) === profileId.value) || null
}

async function loadFiles() {
  const res = await apiListAgentProfileFiles(profileId.value)
  files.value = res.data || []
}

async function loadToggles() {
  const res = await apiGetAgentProfileFileToggles(profileId.value)
  toggles.value = { ...(res.data?.enabled_files || {}) }
  // Default any missing to true (so user sees them enabled by default)
  for (const f of files.value) {
    if (toggles.value[f] === undefined) toggles.value[f] = true
  }
}

async function reloadAll() {
  err.value = ''
  if (!profileId.value) return
  loading.value = true
  try {
    await loadProfileMeta()
    if (!profile.value) {
      err.value = 'Agent profile not found（可能后端重置了 sqlite 数据库，请从“模版管理”列表重新进入）'
      return
    }
    await loadFiles()
    await loadToggles()
    if (!activeFile.value && files.value.length) {
      const first = files.value[0]
      if (first) await openFile(first)
    }
  } catch (e) {
    err.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

async function openFile(name: string) {
  err.value = ''
  activeFile.value = name
  try {
    const res = await apiGetAgentProfileFile(profileId.value, name)
    content.value = res.data.content || ''
  } catch (e) {
    err.value = e instanceof Error ? e.message : String(e)
  }
}

async function saveActive() {
  if (!activeFile.value) return
  saving.value = true
  err.value = ''
  try {
    await apiUpdateAgentProfileFile(profileId.value, activeFile.value, content.value)
    ElMessage.success('已保存')
    // reload toggles/meta to reflect latest state
    await loadProfileMeta()
  } catch (e) {
    err.value = e instanceof Error ? e.message : String(e)
    ElMessage.error(err.value)
  } finally {
    saving.value = false
  }
}

async function saveToggles() {
  savingToggles.value = true
  err.value = ''
  try {
    await apiUpdateAgentProfileFileToggles(profileId.value, toggles.value)
    ElMessage.success('已保存开关')
  } catch (e) {
    err.value = e instanceof Error ? e.message : String(e)
    ElMessage.error(err.value)
  } finally {
    savingToggles.value = false
  }
}

onMounted(reloadAll)
</script>
