<template>
  <ProjectCodeWorkspace
    v-model:project-menu-open="projectMenuOpen"
    :active-group="activeGroup"
    :active-group-id="activeGroupId"
    :project-groups="projectGroups"
    :loading="loading"
    :tree-roots="treeRoots"
    :active-path="activePath"
    :open-dirs="openDirs"
    :show-hidden-files="showHiddenFiles"
    :active-content="activeContent"
    :is-active-dirty="isActiveDirty"
    :saving="saving"
    @reload="reload"
    @select-project="selectProject"
    @open-file="openFile"
    @toggle-dir="toggleDir"
    @update:show-hidden-files="showHiddenFiles = $event"
    @update:content="updateActiveContent"
    @reset="resetActiveContent"
    @copy="copyActiveContent"
    @save-active="saveActiveFile"
    @new-file="openNewFileDialog"
    @new-dir="openNewDirDialog"
    @delete-entry="confirmDeleteEntry"
  />

  <el-dialog v-model="newEntryOpen" :title="newEntryType === 'file' ? '新建文件' : '新建目录'" width="560px" class="newFileDialog" destroy-on-close>
    <el-form label-position="top" class="newFileForm">
      <el-form-item :label="newEntryType === 'file' ? '文件名称' : '目录名称'">
        <el-input v-model="newEntryName" :placeholder="newEntryType === 'file' ? '例如 index.vue' : '例如 components'" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="newEntryOpen = false" :disabled="saving">取消</el-button>
      <el-button type="primary" :loading="saving" @click="createNewEntry">
        {{ newEntryType === 'file' ? '创建并打开' : '创建目录' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  apiCreateProjectCodeDir,
  apiDeleteProjectCodeEntry,
  apiListProjectCode,
  apiReadProjectCodeFile,
  apiWriteProjectCodeFile,
  type Group,
  type ProjectCodeEntry,
} from '../api/project-code'
import { apiListGroups } from '../api/groups'
import ProjectCodeWorkspace from '../components/project-code/ProjectCodeWorkspace.vue'
import { type FileTreeNode } from '../components/AgentFileTreeNode.vue'
import { ElMessage, ElMessageBox } from 'element-plus'

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
const saving = ref(false)
const showHiddenFiles = ref(false)
const newEntryOpen = ref(false)
const newEntryType = ref<'file' | 'dir'>('file')
const newEntryName = ref('')

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

function parentDirFromPath(path: string) {
  const normalized = path.replace(/\\/g, '/').replace(/\/+$/, '')
  const slashIndex = normalized.lastIndexOf('/')
  return slashIndex >= 0 ? normalized.slice(0, slashIndex) : ''
}

function currentBrowserDir() {
  if (activePath.value) return parentDirFromPath(activePath.value)
  const openDirsList = Object.entries(openDirs.value)
    .filter(([, isOpen]) => isOpen)
    .map(([path]) => path.replace(/\/+$/, ''))
    .sort((a, b) => b.length - a.length)
  return openDirsList[0] || ''
}

function normalizeRequestedPath(path: string) {
  return path.replace(/\\/g, '/').replace(/^\/+/, '').replace(/\/+$/, '')
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

function buildTree(rows: ProjectCodeEntry[], showHiddenFiles: boolean): FileTreeNode[] {
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
    const partsAll = splitPath(raw)
    if (!showHiddenFiles && partsAll.some((segment) => segment.startsWith('.'))) continue
    const parts = partsAll
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

const treeRoots = computed(() => buildTree(filteredEntries.value, showHiddenFiles.value))

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

function openNewFileDialog() {
  newEntryType.value = 'file'
  newEntryName.value = 'new-file.txt'
  newEntryOpen.value = true
}

function openNewDirDialog() {
  newEntryType.value = 'dir'
  newEntryName.value = 'new-folder'
  newEntryOpen.value = true
}

async function saveActiveFile() {
  if (!activeGroupId.value || !activePath.value) return
  saving.value = true
  try {
    const content = activeContent.value || ''
    const requestedPath = normalizeRequestedPath(activePath.value)
    const res = await apiWriteProjectCodeFile(activeGroupId.value, requestedPath, content)
    const savedPath = res.data.path || requestedPath
    const key = `${activeGroupId.value}::${savedPath}`
    serverContents.value = { ...serverContents.value, [key]: res.data.content }
    draftContents.value = { ...draftContents.value, [key]: res.data.content }
    saveDraftToStorage(activeGroupId.value, savedPath, res.data.content)
    activePath.value = savedPath
    await reload()
    ElMessage.success('文件已保存')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : String(error))
  } finally {
    saving.value = false
  }
}

async function createNewEntry() {
  if (!activeGroupId.value) return
  const name = normalizeRequestedPath(newEntryName.value.trim())
  if (!name) {
    ElMessage.error(newEntryType.value === 'file' ? '请输入文件名称' : '请输入目录名称')
    return
  }
  if (name.includes('/')) {
    ElMessage.error('这里只需要填写名称，不要包含目录')
    return
  }
  const baseDir = currentBrowserDir()
  const path = normalizeRequestedPath(`${baseDir ? `${baseDir}/` : ''}${name}`)
  if (entries.value.some((item) => normalizeRequestedPath(item.path) === path)) {
    ElMessage.error(newEntryType.value === 'file' ? '文件已存在，请直接打开后编辑' : '目录已存在')
    return
  }
  saving.value = true
  try {
    if (newEntryType.value === 'file') {
      const res = await apiWriteProjectCodeFile(activeGroupId.value, path, '')
      const savedPath = res.data.path || path
      const key = `${activeGroupId.value}::${savedPath}`
      serverContents.value = { ...serverContents.value, [key]: res.data.content }
      draftContents.value = { ...draftContents.value, [key]: res.data.content }
      saveDraftToStorage(activeGroupId.value, savedPath, res.data.content)
      activePath.value = savedPath
      if (baseDir) {
        openDirs.value = { ...openDirs.value, [`${baseDir}/`]: true }
      }
    } else {
      await apiCreateProjectCodeDir(activeGroupId.value, path)
      if (baseDir) {
        openDirs.value = { ...openDirs.value, [`${baseDir}/`]: true }
      }
    }
    await reload()
    newEntryOpen.value = false
    ElMessage.success(newEntryType.value === 'file' ? '文件已创建' : '目录已创建')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : String(error))
  } finally {
    saving.value = false
  }
}

function clearDeletedEntryState(path: string, isDir: boolean) {
  const normalizedPath = normalizeRequestedPath(path)
  const pathPrefix = isDir ? `${normalizedPath.replace(/\/+$/, '')}/` : normalizedPath
  const cachePrefix = `${activeGroupId.value}::`
  const matchesDeletedPath = (entryPath: string) => (isDir ? entryPath.startsWith(pathPrefix) : entryPath === pathPrefix)

  draftContents.value = Object.fromEntries(
    Object.entries(draftContents.value).filter(([key]) => {
      if (!key.startsWith(cachePrefix)) return true
      return !matchesDeletedPath(key.slice(cachePrefix.length))
    }),
  )
  serverContents.value = Object.fromEntries(
    Object.entries(serverContents.value).filter(([key]) => {
      if (!key.startsWith(cachePrefix)) return true
      return !matchesDeletedPath(key.slice(cachePrefix.length))
    }),
  )
  openDirs.value = Object.fromEntries(
    Object.entries(openDirs.value).filter(([dirPath]) => {
      const normalizedDirPath = `${dirPath.replace(/\/+$/, '')}/`
      return !matchesDeletedPath(normalizedDirPath)
    }),
  )
  if (activePath.value && matchesDeletedPath(activePath.value)) {
    activePath.value = ''
  }
}

async function confirmDeleteEntry(target: { path: string; is_dir: boolean; label: string }) {
  if (!activeGroupId.value) return
  const normalizedPath = normalizeRequestedPath(target.path)
  const title = target.is_dir ? '删除目录' : '删除文件'
  const message = target.is_dir
    ? `确定要删除目录「${target.label}」吗？\n该目录及其全部内容都会被永久删除。`
    : `确定要删除文件「${target.label}」吗？\n该文件将被永久删除。`

  try {
    await ElMessageBox.confirm(message, title, {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }

  saving.value = true
  try {
    await apiDeleteProjectCodeEntry(activeGroupId.value, normalizedPath)
    clearDeletedEntryState(normalizedPath, target.is_dir)
    await reload()
    ElMessage.success(target.is_dir ? '目录已删除' : '文件已删除')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : String(error))
  } finally {
    saving.value = false
  }
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
