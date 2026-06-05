<template>
  <div class="shell">
    <div class="header">
      <div class="title">模版详情：{{ profile?.name || profileId }}</div>
      <div class="actions">
        <el-button @click="$emit('back')">返回</el-button>
        <el-button @click="$emit('reload-all')" :disabled="loading">刷新</el-button>
        <el-button type="primary" :loading="saving" :disabled="!activeFile" @click="$emit('save-active')">保存</el-button>
      </div>
    </div>

    <section class="panel">
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
    </section>
  </div>
</template>

<script setup lang="ts">
import type { AgentProfile } from '@/api/models.ts'

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
.header { height:64px; padding:0 10px; display:flex; align-items:center; justify-content:space-between; }
.title { font-weight:900; font-size:16px; }
.actions { display:flex; gap:10px; }
.panel { flex:1; min-height:0; background:rgba(255,255,255,.75); backdrop-filter:blur(12px); border:1px solid rgba(31,35,41,.08); border-radius:18px; overflow:hidden; padding:14px; }
.panelInner { height:100%; display:grid; grid-template-columns:340px 1fr; gap:14px; min-height:0; }
.files { border:1px solid rgba(31,35,41,.08); border-radius:16px; overflow:auto; padding:10px; min-height:0; }
.filesTitle { font-weight:900; margin-bottom:8px; }
.fileList { display:grid; gap:6px; }
.fileItem { padding:10px 10px; border-radius:12px; cursor:pointer; display:flex; justify-content:space-between; align-items:center; }
.fileItem:hover { background:rgba(79,140,255,.06); }
.fileItem.active { background:rgba(79,140,255,.12); }
.fName { font-weight:900; }
.toggleBox { margin-top:12px; border-top:1px solid rgba(31,35,41,.06); padding-top:10px; }
.toggleRow { display:flex; justify-content:space-between; align-items:center; padding:6px 2px; }
.tName { font-weight:800; font-size:12px; opacity:.85; }
.toggleActions { display:flex; justify-content:flex-end; margin-top:10px; }
.editor { border:1px solid rgba(31,35,41,.08); border-radius:16px; overflow:hidden; display:flex; flex-direction:column; min-height:0; }
.editorHeader { height:52px; border-bottom:1px solid rgba(31,35,41,.06); display:flex; align-items:center; padding:0 12px; justify-content:space-between; }
.editorTitle { font-weight:900; }
.editorBody { padding:12px; overflow:auto; min-height:0; }
.err { margin-top:10px; color:#d92d20; font-size:12px; }
.hint { opacity:.6; padding:6px 2px; }
</style>
