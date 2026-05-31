<template>
  <div class="page">
    <div class="hero">
      <div>
        <div class="eyebrow">Project Asset Layer</div>
        <div class="title">项目代码预览</div>
        <div class="sub">浏览 project 群聊对应的 `shared/code` 目录，确认智能体将来读写和生成的正式项目代码资产。</div>
      </div>
      <div class="heroActions">
        <el-select v-model="activeGroupId" placeholder="选择项目群聊" filterable style="width: 280px" @change="onGroupChange">
          <el-option v-for="g in projectGroups" :key="g.id" :label="g.name" :value="g.id" />
        </el-select>
        <el-button @click="reload" :disabled="!activeGroupId" :loading="loading">刷新</el-button>
      </div>
    </div>

    <div class="shell">
      <section class="treePanel">
        <div class="panelHead">
          <div>
            <div class="panelTitle">文件树</div>
            <div class="panelSub">{{ activeGroup?.name || '请先选择项目群聊' }}</div>
          </div>
          <el-input v-model="filter" placeholder="搜索文件…" size="small" style="width: 220px" />
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
        <div class="panelHead">
          <div>
            <div class="panelTitle">{{ activePath || '文件内容' }}</div>
            <div class="panelSub">这里只做预览，后续再接项目代码编辑能力。</div>
          </div>
        </div>
        <div class="contentWrap">
          <div v-if="!activePath" class="empty">从左侧选择一个文件预览内容。</div>
          <pre v-else class="codeBlock">{{ content }}</pre>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  apiListGroups,
  apiListProjectCode,
  apiReadProjectCodeFile,
  type Group,
  type ProjectCodeEntry,
} from '../api/agenthub'
import AgentFileTreeNode, { type FileTreeNode } from '../components/AgentFileTreeNode.vue'

const route = useRoute()
const router = useRouter()
const groups = ref<Group[]>([])
const activeGroupId = ref('')
const entries = ref<ProjectCodeEntry[]>([])
const loading = ref(false)
const filter = ref('')
const activePath = ref('')
const content = ref('')
const openDirs = ref<Record<string, boolean>>({})

const projectGroups = computed(() => groups.value.filter((g) => g.type === 'project'))
const activeGroup = computed(() => projectGroups.value.find((g) => g.id === activeGroupId.value) || null)

const filteredEntries = computed(() => {
  const q = filter.value.trim().toLowerCase()
  if (!q) return entries.value
  return entries.value.filter((item) => item.path.toLowerCase().includes(q))
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
      content.value = ''
    }
  } finally {
    loading.value = false
  }
}

async function onGroupChange() {
  activePath.value = ''
  content.value = ''
  openDirs.value = {}
  await router.replace({ name: 'project-code', query: activeGroupId.value ? { groupId: activeGroupId.value } : {} })
  await reload()
}

async function openFile(path: string) {
  if (!activeGroupId.value) return
  activePath.value = path
  const res = await apiReadProjectCodeFile(activeGroupId.value, path)
  content.value = res.data.content
}

function toggleDir(path: string) {
  openDirs.value = { ...openDirs.value, [path]: !openDirs.value[path] }
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
    content.value = ''
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
  gap: 16px;
}

.hero {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  padding: 20px 22px;
  border-radius: 24px;
  background:
    radial-gradient(circle at left top, rgba(82, 183, 255, 0.2), transparent 30%),
    radial-gradient(circle at right bottom, rgba(255, 212, 120, 0.22), transparent 26%),
    linear-gradient(135deg, #f6fbff 0%, #fff8ef 100%);
  border: 1px solid rgba(31, 35, 41, 0.08);
}

.eyebrow {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: #5f7ea7;
  font-weight: 800;
}

.title {
  margin-top: 8px;
  font-size: 28px;
  font-weight: 900;
}

.sub {
  margin-top: 8px;
  font-size: 14px;
  line-height: 1.7;
  color: rgba(31, 35, 41, 0.7);
  max-width: 760px;
}

.heroActions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.shell {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: 16px;
}

.treePanel,
.contentPanel {
  min-height: 0;
  display: flex;
  flex-direction: column;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(31, 35, 41, 0.08);
  backdrop-filter: blur(12px);
}

.panelHead {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  padding: 16px 18px;
  border-bottom: 1px solid rgba(31, 35, 41, 0.06);
}

.panelTitle {
  font-size: 18px;
  font-weight: 900;
}

.panelSub {
  margin-top: 4px;
  font-size: 12px;
  color: rgba(31, 35, 41, 0.58);
}

.treeWrap,
.contentWrap {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 14px;
}

.codeBlock {
  margin: 0;
  min-height: 100%;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: 'SFMono-Regular', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.7;
  color: #1d2433;
}

.empty {
  padding: 18px 10px;
  color: rgba(31, 35, 41, 0.58);
}

@media (max-width: 1100px) {
  .hero,
  .shell {
    display: grid;
    grid-template-columns: 1fr;
  }
}
</style>
