<template>
  <div class="filesLayout">
    <aside class="leftList">
      <div class="listHeader">核心文件</div>
      <button
        v-for="item in files"
        :key="item.path"
        class="listCard"
        :class="{ active: activeFile === item.value }"
        @click="$emit('select-file', item.value)"
      >
        <div class="listTitle">{{ item.label }}</div>
        <div class="listMeta">{{ item.path }}</div>
      </button>
    </aside>

    <main class="detailPane">
      <div class="detailHeader">
        <div class="detailTitle">{{ activePath }}</div>
        <div class="detailActions">
          <el-button size="small" type="danger" plain @click="$emit('delete-file')" :disabled="!canDelete">
            删除
          </el-button>
        </div>
      </div>
      <CodeMirrorFileEditor
        :path="activePath"
        :content="content"
        :dirty="dirty"
        :saving="saving"
        @update:content="$emit('update:content', $event)"
        @save="$emit('save')"
        @reset="$emit('reset')"
        @copy="$emit('copy')"
      />
      <div v-if="err" class="err">{{ err }}</div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { defineAsyncComponent } from 'vue'

const CodeMirrorFileEditor = defineAsyncComponent(() => import('../CodeMirrorFileEditor.vue'))

defineProps<{
  files: Array<{ label: string; path: string; value: 'SOUL.md' | 'PROFILE.md' | 'BOOTSTRAP.md' | 'MEMORY.md' }>
  activeFile: 'SOUL.md' | 'PROFILE.md' | 'BOOTSTRAP.md' | 'MEMORY.md'
  activePath: string
  content: string
  dirty: boolean
  saving: boolean
  canDelete: boolean
  err: string
}>()

defineEmits<{
  (e: 'select-file', value: 'SOUL.md' | 'PROFILE.md' | 'BOOTSTRAP.md' | 'MEMORY.md'): void
  (e: 'update:content', value: string): void
  (e: 'save'): void
  (e: 'reset'): void
  (e: 'copy'): void
  (e: 'delete-file'): void
}>()
</script>

<style scoped>
.filesLayout {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr);
  gap: 14px;
  min-height: 0;
  flex: 1;
}
.leftList {
  border: 1px solid var(--ah-border-soft);
  border-radius: 16px;
  padding: 10px;
  background: var(--ah-surface-soft);
  display: grid;
  gap: 8px;
  min-height: 0;
  overflow: auto;
  align-content: start;
}
.listHeader { font-weight: 900; margin-bottom: 4px; }
.listCard {
  width: 100%;
  border: 1px solid var(--ah-border-soft);
  border-radius: 12px;
  background: var(--ah-panel-bg);
  padding: 10px 12px;
  text-align: left;
  cursor: pointer;
}
.listCard.active {
  background: var(--ah-conv-item-active-bg, var(--ah-list-active-bg));
  box-shadow: inset 0 0 0 1px var(--ah-conv-item-active-border, var(--ah-list-active-border));
}
.listTitle { font-weight: 900; }
.listMeta {
  margin-top: 2px;
  font-size: 12px;
  color: var(--ah-text-tertiary);
}
.detailPane {
  border: 1px solid var(--ah-border-soft);
  border-radius: 16px;
  padding: 12px;
  background: var(--ah-panel-bg);
  min-height: 0;
  overflow: auto;
  display: flex;
  flex-direction: column;
}
.detailHeader {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
.detailTitle { font-weight: 900; }
.detailActions {
  flex: 0 0 auto;
}
.err {
  margin-top: 10px;
  color: var(--ah-danger);
  font-size: 12px;
}
@media (max-width: 1100px) {
  .filesLayout {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto;
    height: auto;
  }
}
</style>
