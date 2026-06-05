<template>
  <div class="page">
    <div class="shell">
      <section class="treePanel">
        <div class="panelHead">
          <div class="panelTitle">{{ activeGroup?.name || '请选择项目' }}</div>
          <div class="panelHeadActions">
            <el-button class="heroRefresh" :icon="RefreshRight" circle @click="reload" :disabled="!activeGroupId" :loading="loading" />
            <el-popover
              v-model:visible="projectMenuOpen"
              placement="bottom-end"
              trigger="click"
              :width="260"
              :teleported="false"
              popper-class="projectMenuPopover"
            >
              <div class="projectMenuCard">
                <button
                  v-for="g in projectGroups"
                  :key="g.id"
                  class="projectOption"
                  :class="{ active: g.id === activeGroupId }"
                  @click="selectProject(g.id)"
                >
                  <span class="projectName">{{ g.name }}</span>
                  <span class="projectMark" v-if="g.id === activeGroupId">当前</span>
                </button>
              </div>
              <template #reference>
                <el-button class="toggleBtn" :icon="ArrowDown" circle />
              </template>
            </el-popover>
          </div>
        </div>

        <div class="treeWrap">
          <div v-if="!activeGroupId" class="empty">选择一个项目群聊后查看代码目录。</div>
          <div v-else-if="loading" class="empty">加载中…</div>
          <div v-else-if="treeRoots.length === 0" class="empty">当前 `shared/code` 目录还是空的。</div>
          <AgentFileTreeNode
            v-for="node in treeRoots"
            v-else
            :key="node.path"
            :node="node"
            :active-path="activePath"
            :open-dirs="openDirs"
            @open="openFile"
            @toggle="toggleDir"
          />
        </div>
      </section>

      <section class="contentPanel">
        <div class="contentWrap">
          <CodeMirrorFileEditor
            v-if="activePath"
            :path="activePath"
            :content="activeContent"
            :dirty="isActiveDirty"
            @update:content="updateActiveContent"
            @reset="resetActiveContent"
            @copy="copyActiveContent"
          />
          <div v-else class="empty">从左侧选择一个文件开始编辑。</div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowDown, RefreshRight } from '@element-plus/icons-vue'
import {
  apiListGroups,
  apiListProjectCode,
  apiReadProjectCodeFile,
  type Group,
  type ProjectCodeEntry,
} from '../api/agenthub'
import AgentFileTreeNode, { type FileTreeNode } from '../components/AgentFileTreeNode.vue'

const CodeMirrorFileEditor = defineAsyncComponent(() => import('../components/CodeMirrorFileEditor.vue'))

const route = useRoute()
const router = useRouter()
const groups = ref<Group[]>([])
const activeGroupId = ref('')
const entries = ref<ProjectCodeEntry[]>([])
const loading = ref(false)
const filter = ref('')
const activePath = ref('')
const openDirs = ref<Record<string, boolean>>({})
const serverContents = ref<Record<string, string>>({})
const draftContents = ref<Record<string, string>>({})
const projectMenuOpen = ref(false)

const projectGroups = computed(() => groups.value.filter((g) => g.type === 'project'))
const activeGroup = computed(() => projectGroups.value.find((g) => g.id === activeGroupId.value) || null)
const filteredEntries = computed(() => {
  const query = filter.value.trim().toLowerCase()
  if (!query) return entries.value
  return entries.value.filter((item) => item.path.toLowerCase().includes(query))
})
const activeContentKey = computed(() =>
  activeGroupId.value && activePath.value ? `${activeGroupId.value}::${activePath.value}` : '',
)

function draftStorageKey(groupId: string, path: string) {
  return `agenthub.project-code.draft::${groupId}::${path}`
}

function loadDraftFromStorage(groupId: string, path: string) {
  if (typeof window === 'undefined') return null
  return window.localStorage.getItem(draftStorageKey(groupId, path))
}

function saveDraftToStorage(groupId: string, path: string, content: string) {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(draftStorageKey(groupId, path), content)
}

function removeDraftFromStorage(groupId: string, path: string) {
  if (typeof window === 'undefined') return
  window.localStorage.removeItem(draftStorageKey(groupId, path))
}

const activeContent = computed({
  get() {
    const key = activeContentKey.value
    if (!key) return ''
    return draftContents.value[key] ?? serverContents.value[key] ?? ''
  },
  set(value: string) {
    if (!activeContentKey.value) return
    draftContents.value = {
      ...draftContents.value,
      [activeContentKey.value]: value,
    }
    const dividerIndex = activeContentKey.value.indexOf('::')
    if (dividerIndex < 0) return
    const groupId = activeContentKey.value.slice(0, dividerIndex)
    const path = activeContentKey.value.slice(dividerIndex + 2)
    saveDraftToStorage(groupId, path, value)
  },
})

const isActiveDirty = computed(() => {
  const key = activeContentKey.value
  if (!key) return false
  return (draftContents.value[key] ?? '') !== (serverContents.value[key] ?? '')
})

function splitPath(path: string) {
  return path.replace(/\\/g, '/').replace(/^\/+/, '').split('/').filter(Boolean)
}

function buildTree(rows: ProjectCodeEntry[]): FileTreeNode[] {
  const nodes = new Map<string, FileTreeNode>()

  const ensure = (path: string, isDir: boolean, size: number): FileTreeNode => {
    const existing = nodes.get(path)
    if (existing) return existing
    const parts = splitPath(path)
    const last = parts.at(-1) || path.replace(/\/+$/, '')
    const label = path.endsWith('/') ? `${last}/` : last
    const node: FileTreeNode = { path, label, is_dir: isDir, size, children: [] }
    nodes.set(path, node)
    return node
  }

  const roots: FileTreeNode[] = []
  const appendChild = (parent: FileTreeNode | null, child: FileTreeNode) => {
    if (parent) {
      if (!parent.children.some((item) => item.path === child.path)) parent.children.push(child)
      return
    }
    if (!roots.some((item) => item.path === child.path)) roots.push(child)
  }

  for (const row of rows) {
    const raw = row.path
    if (!raw) continue
    const isDir = row.is_dir || raw.endsWith('/')
    const parts = splitPath(raw)
    let parent: FileTreeNode | null = null
    for (let index = 0; index < parts.length; index += 1) {
      const isLast = index === parts.length - 1
      const path = `${parts.slice(0, index + 1).join('/')}${isLast && isDir ? '/' : ''}`
      const node = ensure(path, isLast ? isDir : true, isLast ? row.size || 0 : 0)
      appendChild(parent, node)
      parent = node
    }
  }

  const sortNode = (node: FileTreeNode) => {
    node.children.sort((a, b) => {
      if (a.is_dir !== b.is_dir) return a.is_dir ? -1 : 1
      return a.label.localeCompare(b.label)
    })
    node.children.forEach(sortNode)
  }
  roots.sort((a, b) => {
    if (a.is_dir !== b.is_dir) return a.is_dir ? -1 : 1
    return a.label.localeCompare(b.label)
  })
  roots.forEach(sortNode)
  return roots
}

const treeRoots = computed(() => buildTree(filteredEntries.value))

async function loadGroups() {
  const res = await apiListGroups()
  groups.value = res.data
  if (!activeGroupId.value && projectGroups.value[0]) {
    activeGroupId.value = projectGroups.value[0].id
  }
}

async function reload() {
  if (!activeGroupId.value) return
  loading.value = true
  try {
    const res = await apiListProjectCode(activeGroupId.value)
    entries.value = res.data
    if (activePath.value && !entries.value.some((item) => item.path === activePath.value)) {
      activePath.value = ''
    } else if (activePath.value) {
      await openFile(activePath.value)
    }
  } finally {
    loading.value = false
  }
}

async function onGroupChange() {
  activePath.value = ''
  openDirs.value = {}
  projectMenuOpen.value = false
  await router.replace({ name: 'project-code', query: activeGroupId.value ? { groupId: activeGroupId.value } : {} })
  await reload()
}

async function selectProject(groupId: string) {
  if (groupId === activeGroupId.value) {
    projectMenuOpen.value = false
    return
  }
  activeGroupId.value = groupId
  await onGroupChange()
}

async function openFile(path: string) {
  if (!activeGroupId.value) return
  activePath.value = path
  const storageDraft = loadDraftFromStorage(activeGroupId.value, path)
  const key = `${activeGroupId.value}::${path}`
  if (storageDraft !== null) {
    draftContents.value = { ...draftContents.value, [key]: storageDraft }
  }
  const res = await apiReadProjectCodeFile(activeGroupId.value, path)
  serverContents.value = { ...serverContents.value, [key]: res.data.content }
  if (!(key in draftContents.value)) {
    draftContents.value = { ...draftContents.value, [key]: res.data.content }
  }
}

function toggleDir(path: string) {
  openDirs.value = { ...openDirs.value, [path]: !openDirs.value[path] }
}

function updateActiveContent(value: string) {
  activeContent.value = value
}

function resetActiveContent() {
  if (!activeContentKey.value || !activeGroupId.value || !activePath.value) return
  const key = activeContentKey.value
  const serverContent = serverContents.value[key] ?? ''
  draftContents.value = { ...draftContents.value, [key]: serverContent }
  removeDraftFromStorage(activeGroupId.value, activePath.value)
}

async function copyActiveContent() {
  await navigator.clipboard.writeText(activeContent.value || '')
}

onMounted(async () => {
  await loadGroups()
  const initialGroupId = String(route.query.groupId || '')
  if (initialGroupId && projectGroups.value.some((item) => item.id === initialGroupId)) {
    activeGroupId.value = initialGroupId
  }
  if (activeGroupId.value) {
    await reload()
  }
})

watch(
  () => route.query.groupId,
  async (value) => {
    const next = String(value || '')
    if (!next || next === activeGroupId.value) return
    if (!projectGroups.value.some((item) => item.id === next)) return
    activeGroupId.value = next
    activePath.value = ''
    openDirs.value = {}
    await reload()
  },
)
</script>

<style scoped>
.page {
  height: calc(100vh - 36px);
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.panelHead {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 14px 12px 10px;
  border-bottom: 1px solid rgba(31, 35, 41, 0.06);
}

.panelHeadActions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.heroRefresh {
  flex: 0 0 auto;
}

.toggleBtn {
  flex: 0 0 auto;
}

.projectMenuCard {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

:global(.projectMenuPopover) {
  padding: 10px;
  border-radius: 16px;
}

.panelTitle {
  font-size: 15px;
  font-weight: 800;
  color: rgba(31, 35, 41, 0.86);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.projectOption {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  border: 0;
  border-radius: 12px;
  padding: 10px 12px;
  background: rgba(31, 35, 41, 0.03);
  color: rgba(31, 35, 41, 0.78);
  cursor: pointer;
  text-align: left;
}

.projectOption:hover,
.projectOption.active {
  background: rgba(64, 158, 255, 0.1);
  color: rgba(31, 35, 41, 0.92);
}

.projectName {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.projectMark {
  flex: 0 0 auto;
  font-size: 12px;
  color: rgba(31, 35, 41, 0.45);
}

.shell {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 340px minmax(0, 1fr);
  gap: 12px;
}

.treePanel,
.contentPanel {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid rgba(31, 35, 41, 0.08);
  backdrop-filter: blur(10px);
}

.treeWrap,
.contentWrap {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 12px;
}

.contentWrap {
  min-height: 0;
  display: flex;
}

.empty {
  padding: 18px 10px;
  color: rgba(31, 35, 41, 0.58);
}

@media (max-width: 1100px) {
  .shell {
    display: grid;
    grid-template-columns: 1fr;
  }

  .treePanel,
  .contentPanel {
    height: auto;
    min-height: 0;
  }
}
</style>
