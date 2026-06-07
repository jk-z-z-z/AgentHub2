<template>
  <div class="shell">
    <WorkspacePanel :title="`模版详情：${profile?.name || profileId}`">
      <template #actions>
        <el-button @click="$emit('back')">返回</el-button>
        <el-button @click="$emit('reload-all')" :disabled="loading">刷新</el-button>
        <el-button type="primary" :loading="saving" :disabled="!activeFile" @click="$emit('save-active')">保存</el-button>
      </template>

      <div class="panelInner">
        <aside class="files">
          <div class="filesTitle">文件</div>
          <div v-if="loading" class="hint">加载中…</div>
          <div class="fileList">
            <div
              v-for="f in files"
              :key="f"
              class="fileItem"
              :class="{ active: f === activeFile }"
              @click="$emit('open-file', f)"
            >
              <div class="fName">{{ f }}</div>
              <div class="fMeta">
                <el-tag v-if="toggles[f]" type="success" size="small">启用</el-tag>
                <el-tag v-else-if="!toggles[f]" type="info" size="small">关闭</el-tag>
              </div>
            </div>
          </div>

          <div class="toggleBox">
            <div style="font-weight: 900; margin-bottom: 6px">文件开关</div>
            <div class="toggleRow" v-for="f in files" :key="`t_${f}`">
              <div class="tName">{{ f }}</div>
              <el-switch v-model="toggles[f]" />
            </div>
            <div class="toggleActions">
              <el-button size="small" @click="$emit('save-toggles')" :loading="savingToggles">保存开关</el-button>
            </div>
          </div>
        </aside>

        <main class="editor">
          <div class="editorHeader">
            <div class="editorTitle">{{ activeFile || '选择一个文件' }}</div>
          </div>
          <div class="editorBody">
            <div v-if="!activeFile" class="hint">从左侧选择文件</div>
            <el-input v-else v-model="contentModel" type="textarea" :rows="24" placeholder="编辑内容" />
            <div v-if="err" class="err">{{ err }}</div>
          </div>
        </main>
      </div>
    </WorkspacePanel>
  </div>
</template>

<script setup lang="ts">
import type { AgentProfile } from '@/api/models.ts'
import WorkspacePanel from '../common/WorkspacePanel.vue'

const contentModel = defineModel<string>('content', { required: true })

defineProps<{
  profileId: string
  profile: AgentProfile | null
  files: string[]
  toggles: Record<string, boolean>
  activeFile: string
  loading: boolean
  saving: boolean
  savingToggles: boolean
  err: string
}>()

defineEmits<{
  (e: 'back'): void
  (e: 'reload-all'): void
  (e: 'open-file', name: string): void
  (e: 'save-active'): void
  (e: 'save-toggles'): void
}>()
</script>

<style scoped>
.shell { height: 100%; display:flex; flex-direction:column; gap:14px; }
.shell :deep(.el-button) { box-shadow: none; }
.shell :deep(.el-button:not(.el-button--primary):not(.el-button--danger)) {
  --el-button-bg-color: var(--ah-surface-soft);
  --el-button-border-color: transparent;
  --el-button-text-color: var(--ah-text-primary);
  --el-button-hover-bg-color: var(--ah-conv-item-hover-bg, var(--ah-hover-strong));
  --el-button-hover-border-color: transparent;
  --el-button-hover-text-color: var(--ah-text-primary);
  --el-button-active-bg-color: var(--ah-conv-item-active-bg, var(--ah-list-active-bg));
  --el-button-active-border-color: transparent;
  --el-button-active-text-color: var(--ah-text-primary);
}
.shell :deep(.el-button--primary) {
  --el-button-bg-color: color-mix(in srgb, var(--ah-text-strong) 42%, transparent);
  --el-button-border-color: transparent;
  --el-button-text-color: var(--ah-text-on-primary);
  --el-button-hover-bg-color: color-mix(in srgb, var(--ah-text-strong) 46%, transparent);
  --el-button-hover-border-color: transparent;
  --el-button-hover-text-color: var(--ah-text-on-primary);
  --el-button-active-bg-color: color-mix(in srgb, var(--ah-text-strong) 50%, transparent);
  --el-button-active-border-color: transparent;
  --el-button-active-text-color: var(--ah-text-on-primary);
  --el-button-disabled-bg-color: var(--ah-surface-soft);
  --el-button-disabled-border-color: transparent;
  --el-button-disabled-text-color: var(--ah-text-muted);
}
.panelInner { flex:1; min-height:0; display:grid; grid-template-columns:340px 1fr; gap:14px; }
.files { border:1px solid var(--ah-border); border-radius:16px; overflow:auto; padding:10px; min-height:0; }
.filesTitle { font-weight:900; margin-bottom:8px; }
.fileList { display:grid; gap:6px; }
.fileItem {
  padding:10px 10px;
  border-radius:12px;
  cursor:pointer;
  display:flex;
  justify-content:space-between;
  align-items:center;
  transition:
    background-color 0.18s ease,
    color 0.18s ease,
    box-shadow 0.18s ease;
}
.fileItem:hover { background:var(--ah-conv-item-hover-bg, var(--ah-hover-strong)); }
.fileItem.active {
  background:var(--ah-conv-item-active-bg, var(--ah-list-active-bg));
  box-shadow: inset 0 0 0 1px var(--ah-conv-item-active-border, var(--ah-list-active-border));
}
.fileItem.active .fName { color: var(--ah-text-primary); }
.fName { font-weight:900; }
.shell :deep(.el-switch) {
  --el-switch-on-color: color-mix(in srgb, var(--ah-text-strong) 42%, transparent);
  --el-switch-off-color: var(--ah-border-strong);
}
.toggleBox { margin-top:12px; border-top:1px solid var(--ah-border-soft); padding-top:10px; }
.toggleRow { display:flex; justify-content:space-between; align-items:center; padding:6px 2px; }
.tName { font-weight:800; font-size:12px; opacity:.85; }
.toggleActions { display:flex; justify-content:flex-end; margin-top:10px; }
.editor { border:1px solid var(--ah-border); border-radius:16px; overflow:hidden; display:flex; flex-direction:column; min-height:0; }
.editorHeader { height:52px; border-bottom:1px solid var(--ah-border-soft); display:flex; align-items:center; padding:0 12px; justify-content:space-between; }
.editorTitle { font-weight:900; }
.editorBody { padding:12px; overflow:auto; min-height:0; }
.err { margin-top:10px; color:var(--ah-danger); font-size:12px; }
.hint { opacity:.6; padding:6px 2px; }
</style>
