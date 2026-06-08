<template>
  <div class="sidePanel">
    <div class="sideHeader">
      <div>
        <div class="sideTitle">文件树</div>
        <div class="sideSubtitle">只查看项目目录结构</div>
      </div>
      <div class="sideHeaderActions">
        <el-button
          class="refreshBtn"
          size="small"
          :icon="RefreshRight"
          @click="$emit('refresh')"
          :loading="loading"
          aria-label="刷新文件目录"
        />
        <el-button class="sideCloseBtn" :icon="Close" circle text @click="$emit('close')" aria-label="关闭文件树" />
      </div>
    </div>

    <el-scrollbar class="sideBody">
      <div v-if="supportsProjectWorkspace" class="fileShell">
        <el-card class="fileTreeWrap" shadow="never">
          <div v-if="loading" class="taskEmpty">加载文件目录中…</div>
          <div v-else-if="projectRoots.length === 0" class="taskEmpty">当前项目还没有可展示的文件</div>
          <template v-else>
            <AgentFileTreeNode
              v-for="node in projectRoots"
              :key="node.path"
              :node="node"
              :active-path="activePath"
              :open-dirs="openDirs"
              @open="$emit('open-file', $event)"
              @toggle="$emit('toggle-dir', $event)"
            />
          </template>
        </el-card>
      </div>
      <div v-else class="sideEmpty">
        <div class="empty">仅项目群聊支持文件目录</div>
      </div>
    </el-scrollbar>
  </div>
</template>

<script setup lang="ts">
import { Close, RefreshRight } from '@element-plus/icons-vue'
import { computed } from 'vue'
import AgentFileTreeNode, { type FileTreeNode } from '../../components/AgentFileTreeNode.vue'
import type { Group, ProjectCodeEntry } from '@/api/models.ts'

const props = defineProps<{
  activeGroup: Group | null
  loading: boolean
  roots: ProjectCodeEntry[]
  activePath: string
  openDirs: Record<string, boolean>
}>()

defineEmits<{
  (e: 'close'): void
  (e: 'refresh'): void
  (e: 'open-file', path: string): void
  (e: 'toggle-dir', path: string): void
}>()

const projectRoots = computed(() => buildProjectTree(props.roots))
const supportsProjectWorkspace = computed(() => {
  const group = props.activeGroup
  if (!group) return false
  return String(group.type || '') === 'project' || Number(group.workspace_id || 0) > 0
})

function buildProjectTree(rows: ProjectCodeEntry[]): FileTreeNode[] {
  const nodes = new Map<string, FileTreeNode>()
  const roots: FileTreeNode[] = []

  const appendChild = (parent: FileTreeNode | null, child: FileTreeNode) => {
    if (parent) {
      if (!parent.children.some((item) => item.path === child.path)) parent.children.push(child)
      return
    }
    if (!roots.some((item) => item.path === child.path)) roots.push(child)
  }

  for (const row of rows) {
    const raw = String(row.path || '')
    if (!raw) continue
    const segments = raw.replace(/\\/g, '/').replace(/^\/+/, '').split('/').filter(Boolean)
    if (segments.length === 0) continue
    const isDir = Boolean(row.is_dir) || raw.endsWith('/')

    let parent: FileTreeNode | null = null
    for (let index = 0; index < segments.length; index += 1) {
      const isLast = index === segments.length - 1
      const segment = segments[index]
      if (!segment) continue
      const path = `${segments.slice(0, index + 1).join('/')}${isLast && isDir ? '/' : ''}`
      let node = nodes.get(path)
      if (!node) {
        node = {
          path,
          label: path.endsWith('/') ? `${segment}/` : segment,
          is_dir: isLast ? isDir : true,
          size: isLast ? Number((row as ProjectCodeEntry).size || 0) : 0,
          children: [],
        }
        nodes.set(path, node)
      }
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
</script>

<style scoped>
.sidePanel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--ah-panel-bg);
  backdrop-filter: blur(10px);
  border: 1px solid var(--ah-panel-border, var(--ah-border));
  border-radius: 18px;
  overflow: hidden;
  min-width: 0;
}
.sideHeader {
  height: 56px;
  padding: 0 16px;
  border-bottom: 1px solid var(--ah-border-soft);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex: 0 0 auto;
}
.sideTitle {
  font-size: 16px;
  font-weight: 900;
}
.sideSubtitle {
  margin-top: 2px;
  font-size: 12px;
  color: var(--ah-text-tertiary);
}
.sideHeaderActions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.sideCloseBtn {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  color: var(--ah-text-secondary);
}
.sideBody {
  flex: 1;
  min-height: 0;
  padding: 12px;
}
.fileShell {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}
.fileTreeWrap {
  border: 1px solid var(--ah-border-soft);
  border-radius: 16px;
  background: var(--ah-surface-soft);
  overflow: auto;
  min-height: 0;
  flex: 1;
}
.fileTreeWrap :deep() {
  margin-bottom: 4px;
}
.taskEmpty {
  padding: 16px 4px;
  font-size: 13px;
  color: var(--ah-text-tertiary);
}
.sideEmpty {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
