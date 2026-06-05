<template>
  <div class="node">
    <div class="nodeRow" :class="{ active: activePath === node.path }" @click="onClick">
      <div class="chev">
        <el-icon v-if="node.is_dir">
          <ArrowDown v-if="isOpen" />
          <ArrowRight v-else />
        </el-icon>
      </div>
      <div class="nIcon">
        <el-icon v-if="node.is_dir">
          <FolderOpened />
        </el-icon>
        <el-icon v-else>
          <Document />
        </el-icon>
      </div>
      <div class="nName">{{ node.label }}</div>
      <div class="nMeta">{{ node.is_dir ? '' : formatSize(node.size) }}</div>
    </div>

    <div v-if="node.is_dir && isOpen" class="children">
      <AgentFileTreeNode
        v-for="c in node.children"
        :key="c.path"
        :node="c"
        :active-path="activePath"
        :open-dirs="openDirs"
        @open="$emit('open', $event)"
        @toggle="$emit('toggle', $event)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ArrowDown, ArrowRight, Document, FolderOpened } from '@element-plus/icons-vue'

export type FileTreeNode = {
  path: string
  label: string
  is_dir: boolean
  size: number
  children: FileTreeNode[]
}

const props = defineProps<{
  node: FileTreeNode
  activePath: string
  openDirs: Record<string, boolean>
}>()

const emit = defineEmits<{
  (e: 'open', path: string): void
  (e: 'toggle', path: string): void
}>()

function formatSize(n: number) {
  if (!n) return '0 B'
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

const isOpen = computed(() => !!props.openDirs[props.node.path])

function onClick() {
  if (props.node.is_dir) {
    emit('toggle', props.node.path)
    return
  }
  emit('open', props.node.path)
}
</script>

<style scoped>
.nodeRow {
  display: grid;
  grid-template-columns: 18px 18px 1fr auto;
  gap: 8px;
  align-items: center;
  padding: 8px 10px;
  border-radius: 12px;
  cursor: pointer;
}
.nodeRow:hover {
  background: rgba(79, 140, 255, 0.06);
}
.nodeRow.active {
  background: rgba(79, 140, 255, 0.12);
}
.chev {
  width: 18px;
  display: inline-flex;
  justify-content: center;
  opacity: 0.7;
}
.nIcon {
  width: 18px;
  display: inline-flex;
  justify-content: center;
  color: rgba(31, 35, 41, 0.62);
}
.nName {
  font-weight: 800;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.nMeta {
  font-size: 12px;
  opacity: 0.65;
}
.children {
  margin-left: 12px;
  border-left: 1px solid rgba(31, 35, 41, 0.08);
  padding-left: 10px;
  display: grid;
  gap: 3px;
}
</style>
