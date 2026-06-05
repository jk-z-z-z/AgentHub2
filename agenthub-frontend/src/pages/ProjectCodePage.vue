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
    :active-content="activeContent"
    :is-active-dirty="isActiveDirty"
    @reload="reload"
    @select-project="selectProject"
    @open-file="openFile"
    @toggle-dir="toggleDir"
    @update:content="updateActiveContent"
    @reset="resetActiveContent"
    @copy="copyActiveContent"
  />
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  apiListProjectCode,
  apiReadProjectCodeFile,
  type Group,
  type ProjectCodeEntry,
} from '../api/project-code'
import { apiListGroups } from '../api/groups'
import ProjectCodeWorkspace from '../components/project-code/ProjectCodeWorkspace.vue'
import { type FileTreeNode } from '../components/AgentFileTreeNode.vue'

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
