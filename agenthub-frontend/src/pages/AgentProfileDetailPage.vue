<template>
  <div class="shell">
    <div class="header">
      <div class="title">模版详情：{{ profile?.name || profileId }}</div>
      <div class="actions">
        <el-button @click="router.push('/agents')">返回</el-button>
        <el-button @click="reloadAll" :disabled="loading">刷新</el-button>
        <el-button type="primary" :loading="saving" :disabled="!activeFile" @click="saveActive">保存</el-button>
      </div>
    </div>

    <section class="panel">
      <div class="panelInner">
        <aside class="files">
          <div class="filesTitle">文件</div>
          <div v-if="loading" class="hint">加载中…</div>
          <div class="fileList">
            <div
              v-for="f in files"
              :key="f"
              class="fileItem"
              :class="{ active: f === activeFile }"
              @click="openFile(f)"
            >
              <div class="fName">{{ f }}</div>
              <div class="fMeta">
                <el-tag v-if="toggles[f] === true" type="success" size="small">启用</el-tag>
                <el-tag v-else-if="toggles[f] === false" type="info" size="small">关闭</el-tag>
              </div>
            </div>
          </div>

          <div class="toggleBox">
            <div style="font-weight: 900; margin-bottom: 6px">文件开关</div>
            <div class="toggleRow" v-for="f in files" :key="`t_${f}`">
              <div class="tName">{{ f }}</div>
              <el-switch v-model="toggles[f]" />
            </div>
            <div class="toggleActions">
              <el-button size="small" @click="saveToggles" :loading="savingToggles">保存开关</el-button>
            </div>
          </div>
        </aside>

        <main class="editor">
          <div class="editorHeader">
            <div class="editorTitle">{{ activeFile || '选择一个文件' }}</div>
          </div>
          <div class="editorBody">
            <div v-if="!activeFile" class="hint">从左侧选择文件</div>
            <el-input v-else v-model="content" type="textarea" :rows="24" placeholder="编辑内容" />
            <div v-if="err" class="err">{{ err }}</div>
          </div>
        </main>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { httpGet, httpPut } from '../api/http'
import { ElMessage } from 'element-plus'
import { apiListAgentProfiles, apiGetAgentProfileFile, apiUpdateAgentProfileFile, type AgentProfile } from '../api/agenthub'

type TogglesResp = { enabled_files: Record<string, boolean> }

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
  const res = await httpGet<string[]>(`/api/v1/agent-profiles/${profileId.value}/files`)
  files.value = res.data || []
}

async function loadToggles() {
  const res = await httpGet<TogglesResp>(`/api/v1/agent-profiles/${profileId.value}/file-toggles`)
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
    await httpPut<TogglesResp, Record<string, boolean>>(
      `/api/v1/agent-profiles/${profileId.value}/file-toggles`,
      toggles.value,
    )
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

<style scoped>
.shell {
  height: calc(100vh - 36px);
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.header {
  height: 64px;
  padding: 0 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.title {
  font-weight: 900;
  font-size: 16px;
}
.actions {
  display: flex;
  gap: 10px;
}
.panel {
  flex: 1;
  min-height: 0;
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 18px;
  overflow: hidden;
  padding: 14px;
}
.panelInner {
  height: 100%;
  display: grid;
  grid-template-columns: 340px 1fr;
  gap: 14px;
  min-height: 0;
}
.files {
  border: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 16px;
  overflow: auto;
  padding: 10px;
  min-height: 0;
}
.filesTitle {
  font-weight: 900;
  margin-bottom: 8px;
}
.fileList {
  display: grid;
  gap: 6px;
}
.fileItem {
  padding: 10px 10px;
  border-radius: 12px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.fileItem:hover {
  background: rgba(79, 140, 255, 0.06);
}
.fileItem.active {
  background: rgba(79, 140, 255, 0.12);
}
.fName {
  font-weight: 900;
}
.toggleBox {
  margin-top: 12px;
  border-top: 1px solid rgba(31, 35, 41, 0.06);
  padding-top: 10px;
}
.toggleRow {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 2px;
}
.tName {
  font-weight: 800;
  font-size: 12px;
  opacity: 0.85;
}
.toggleActions {
  display: flex;
  justify-content: flex-end;
  margin-top: 10px;
}
.editor {
  border: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 16px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.editorHeader {
  height: 52px;
  border-bottom: 1px solid rgba(31, 35, 41, 0.06);
  display: flex;
  align-items: center;
  padding: 0 12px;
  justify-content: space-between;
}
.editorTitle {
  font-weight: 900;
}
.editorBody {
  padding: 12px;
  overflow: auto;
  min-height: 0;
}
.err {
  margin-top: 10px;
  color: #d92d20;
  font-size: 12px;
}
.hint {
  opacity: 0.6;
  padding: 6px 2px;
}
</style>
