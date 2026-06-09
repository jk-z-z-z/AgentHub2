<template>
  <aside class="files">
    <div class="filesHeader">
      <div class="filesTitle">文件</div>
      <div class="hiddenToggle">
        <span class="hiddenToggleLabel">隐藏文件</span>
        <el-switch
          :model-value="showHiddenFiles"
          inline-prompt
          @change="$emit('update:show-hidden-files', Boolean($event))"
        />
      </div>
    </div>
    <div v-if="loading" class="hint">加载中…</div>
    <el-input
      :model-value="filter"
      placeholder="搜索文件…"
      size="small"
      style="margin: 6px 0 10px 0"
      @update:model-value="$emit('update:filter', String($event))"
    />

    <div class="tree">
      <AgentFileTreeNode
        v-for="n in treeRoots"
        :key="n.path"
        :node="n"
        :active-path="activeFilePath"
        :open-dirs="openDirs"
        @open="$emit('open-file', $event)"
        @toggle="$emit('toggle-dir', $event)"
        @delete="$emit('delete-entry', $event)"
      />
    </div>

    <div class="ops">
      <el-select
        :model-value="newFileDir"
        style="width: 140px"
        @update:model-value="handleNewFileDirUpdate"
      >
        <el-option label="skills/" value="skills/" />
        <el-option label="knowledge/" value="knowledge/" />
        <el-option label="mcps/" value="mcps/" />
      </el-select>
      <el-input
        :model-value="newFilePath"
        placeholder="例如：web/search.md 或 notes.md"
        @update:model-value="handleNewFilePathUpdate"
      />
      <el-button type="primary" @click="$emit('create-file')" :disabled="!newFilePath.trim()">
        新建
      </el-button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import AgentFileTreeNode, { type FileTreeNode } from '../AgentFileTreeNode.vue'

defineProps<{
  loading: boolean
  showHiddenFiles: boolean
  filter: string
  treeRoots: FileTreeNode[]
  activeFilePath: string
  openDirs: Record<string, boolean>
  newFileDir: 'skills/' | 'knowledge/' | 'mcps/'
  newFilePath: string
}>()

const emit = defineEmits<{
  (e: 'update:show-hidden-files', value: boolean): void
  (e: 'update:filter', value: string): void
  (e: 'update:new-file-dir', value: 'skills/' | 'knowledge/' | 'mcps/'): void
  (e: 'update:new-file-path', value: string): void
  (e: 'open-file', path: string): void
  (e: 'toggle-dir', path: string): void
  (e: 'delete-entry', payload: { path: string; is_dir: boolean; label: string }): void
  (e: 'create-file'): void
}>()

function handleNewFileDirUpdate(value: string | number | boolean) {
  const next = String(value) as 'skills/' | 'knowledge/' | 'mcps/'
  if (next === 'skills/' || next === 'knowledge/' || next === 'mcps/') {
    emit('update:new-file-dir', next)
  }
}

function handleNewFilePathUpdate(value: string | number | boolean) {
  emit('update:new-file-path', String(value))
}
</script>

<style scoped>
.files {
  border: 1px solid var(--ah-border-soft);
  border-radius: 16px;
  overflow: auto;
  padding: 10px;
  min-height: 0;
}
.filesTitle {
  font-weight: 900;
  margin-bottom: 8px;
}
.filesHeader {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}
.hiddenToggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--ah-text-secondary);
}
.hiddenToggleLabel {
  font-size: 12px;
  white-space: nowrap;
}
.tree {
  display: grid;
  gap: 4px;
}
.hint {
  opacity: 0.6;
  padding: 6px 2px;
}
.ops {
  margin-top: 12px;
  border-top: 1px solid var(--ah-border-soft);
  padding-top: 10px;
  display: grid;
  grid-template-columns: 140px 1fr 80px;
  gap: 8px;
  align-items: center;
}
</style>
