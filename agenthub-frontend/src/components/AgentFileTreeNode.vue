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
      <div class="nActions" @click.stop>
        <el-button
          v-if="!node.is_dir"
          class="nodeActionBtn"
          text
          :icon="Delete"
          title="删除文件"
          aria-label="删除文件"
          @click.stop="$emit('delete', { path: node.path, is_dir: node.is_dir, label: node.label })"
        />
      </div>
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
        @delete="$emit('delete', $event)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ArrowDown, ArrowRight, Delete, Document, FolderOpened } from '@element-plus/icons-vue'

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
  (e: 'delete', payload: { path: string; is_dir: boolean; label: string }): void
}>()

function formatSize(n: number) {
  if (!n) return '0 B'
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

const isOpen = computed(() => props.openDirs[props.node.path])

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
  grid-template-columns: 18px 18px 1fr auto auto;
  gap: 8px;
  align-items: center;
  padding: 8px 10px;
  border-radius: 12px;
  cursor: pointer;
  transition:
    background-color 0.18s ease,
    color 0.18s ease,
    box-shadow 0.18s ease;
}
.nodeRow:hover {
  background: var(--ah-conv-item-hover-bg, var(--ah-hover-strong));
}
.nodeRow.active {
  background: var(--ah-conv-item-active-bg, var(--ah-list-active-bg));
  box-shadow: inset 0 0 0 1px var(--ah-conv-item-active-border, var(--ah-list-active-border));
}
.nodeRow.active .nName {
  color: var(--ah-text-primary);
}
.nodeRow.active .nIcon,
.nodeRow.active .nMeta,
.nodeRow.active .chev {
  color: var(--ah-text-secondary);
  opacity: 1;
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
  color: var(--ah-text-tertiary);
}
.nName {
  font-weight: 800;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.nMeta {
  font-size: 12px;
  color: var(--ah-text-tertiary);
}
.nActions {
  display: flex;
  align-items: center;
  opacity: 0;
  transition: opacity 0.18s ease;
}
.nodeRow:hover .nActions,
.nodeRow.active .nActions {
  opacity: 1;
}
.nodeActionBtn {
  width: 26px;
  height: 26px;
  min-width: 26px;
  padding: 0;
  color: var(--ah-text-tertiary);
}
.nodeActionBtn:hover {
  color: var(--el-color-danger);
}
.children {
  margin-left: 12px;
  border-left: 1px solid var(--ah-border);
  padding-left: 10px;
  display: grid;
  gap: 3px;
}
</style>
