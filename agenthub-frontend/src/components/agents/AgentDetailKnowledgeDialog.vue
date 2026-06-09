<template>
  <el-dialog v-model="openModel" title="编辑知识库文件" width="80%" top="6vh">
    <div class="dialogMeta">{{ path }}</div>
    <CodeMirrorFileEditor
      :path="path"
      :content="content"
      :dirty="dirty"
      :saving="saving"
      @update:content="$emit('update:content', $event)"
      @save="$emit('save')"
      @reset="$emit('reset')"
      @copy="$emit('copy')"
    />
    <div v-if="err" class="err">{{ err }}</div>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent } from 'vue'

const CodeMirrorFileEditor = defineAsyncComponent(() => import('../CodeMirrorFileEditor.vue'))

const props = defineProps<{
  open: boolean
  path: string
  content: string
  dirty: boolean
  saving: boolean
  err: string
}>()

const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'update:content', value: string): void
  (e: 'save'): void
  (e: 'reset'): void
  (e: 'copy'): void
}>()

const openModel = computed({
  get: () => props.open,
  set: (value: boolean) => emit('update:open', value),
})
</script>

<style scoped>
.dialogMeta {
  margin-bottom: 10px;
  font-size: 12px;
  color: var(--ah-text-tertiary);
}
.err {
  margin-top: 10px;
  color: var(--ah-danger);
  font-size: 12px;
}
:deep(.el-dialog__body) {
  min-height: 0;
  padding-bottom: 12px;
}
</style>
