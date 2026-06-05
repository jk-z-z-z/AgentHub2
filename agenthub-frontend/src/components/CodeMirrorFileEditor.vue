<template>
  <div class="editorShell" :style="editorStyle">
    <div class="editorToolbar">
      <div class="fileMeta">
        <div class="filePath">{{ path || '文件内容' }}</div>
        <div class="fileInfo">
          {{ languageLabel }} · {{ lineCount }} 行
          <span v-if="dirty" class="dirtyFlag">· 草稿未保存</span>
        </div>
      </div>

      <div class="toolbarActions">
        <el-select v-model="fontSize" class="fontSelect" size="small" aria-label="选择字体大小">
          <el-option v-for="size in fontSizes" :key="size" :label="`${size}px`" :value="size" />
        </el-select>
        <el-button class="actionBtn" size="small" :disabled="!dirty" @click="$emit('reset')">还原</el-button>
        <el-button class="actionBtn" size="small" @click="$emit('copy')">复制</el-button>
      </div>
    </div>

    <div ref="mountEl" class="editorMount">
      <div v-if="!path" class="emptyState">从左侧选择一个文件开始编辑。</div>
      <div v-else-if="loading" class="emptyState">编辑器加载中…</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { basicSetup } from 'codemirror'
import { EditorState } from '@codemirror/state'
import { EditorView } from '@codemirror/view'

type LanguageId = 'javascript' | 'typescript' | 'json' | 'css' | 'html' | 'markdown' | 'plaintext'

const props = defineProps<{
  path: string
  content: string
  dirty: boolean
}>()

const emit = defineEmits<{
  (e: 'update:content', value: string): void
  (e: 'reset'): void
  (e: 'copy'): void
}>()

const mountEl = ref<HTMLElement | null>(null)
const editorView = ref<EditorView | null>(null)
const loading = ref(false)
const fontSize = ref(11)
const fontSizes = [11, 12, 13, 14, 15, 16, 18]

const language = computed(() => detectLanguage(props.path))
const editorStyle = computed(() => ({
  '--editor-font-size': `${fontSize.value}px`,
}))
const languageLabel = computed(() => {
  if (language.value === 'typescript') return 'TypeScript'
  if (language.value === 'javascript') return 'JavaScript'
  if (language.value === 'json') return 'JSON'
  if (language.value === 'css') return 'CSS'
  if (language.value === 'html') return 'HTML'
  if (language.value === 'markdown') return 'Markdown'
  return 'Plain text'
})
const lineCount = computed(() => {
  if (!props.content) return 0
  return props.content.split(/\r?\n/).length
})

function detectLanguage(path: string): LanguageId {
  const ext = path.toLowerCase().split('.').pop() || ''
  if (['ts', 'tsx'].includes(ext)) return 'typescript'
  if (['js', 'jsx', 'mjs', 'cjs'].includes(ext)) return 'javascript'
  if (ext === 'json') return 'json'
  if (['css', 'scss', 'less'].includes(ext)) return 'css'
  if (['html', 'htm', 'vue'].includes(ext)) return 'html'
  if (['md', 'markdown'].includes(ext)) return 'markdown'
  return 'plaintext'
}

function editorTheme() {
  return EditorView.theme({
    '&': {
      height: '100%',
      backgroundColor: '#fff',
    },
    '.cm-scroller': {
      fontFamily:
        'ui-monospace, SFMono-Regular, SF Mono, Consolas, Liberation Mono, Menlo, monospace',
    },
    '.cm-content, .cm-gutter': {
      minHeight: '100%',
      fontSize: 'var(--editor-font-size)',
    },
    '.cm-gutters': {
      borderRight: '1px solid rgba(31, 35, 41, 0.08)',
      backgroundColor: 'rgba(247, 248, 250, 0.95)',
      color: 'rgba(31, 35, 41, 0.48)',
    },
    '.cm-activeLine, .cm-activeLineGutter': {
      backgroundColor: 'rgba(79, 140, 255, 0.06)',
    },
    '.cm-cursor, .cm-dropCursor': {
      borderLeftColor: '#2563eb',
    },
    '.cm-focused': {
      outline: 'none',
    },
  })
}

async function loadLanguageExtension(path: string) {
  const currentLanguage = detectLanguage(path)
  switch (currentLanguage) {
    case 'typescript': {
      const { javascript } = await import('@codemirror/lang-javascript')
      return javascript({ typescript: true, jsx: true })
    }
    case 'javascript': {
      const { javascript } = await import('@codemirror/lang-javascript')
      return javascript({ typescript: false, jsx: true })
    }
    case 'json': {
      const { json } = await import('@codemirror/lang-json')
      return json()
    }
    case 'css': {
      const { css } = await import('@codemirror/lang-css')
      return css()
    }
    case 'html': {
      const { html } = await import('@codemirror/lang-html')
      return html()
    }
    case 'markdown': {
      const { markdown } = await import('@codemirror/lang-markdown')
      return markdown()
    }
    default:
      return []
  }
}

function disposeEditor() {
  editorView.value?.destroy()
  editorView.value = null
}

async function renderEditor() {
  if (!mountEl.value || !props.path) {
    disposeEditor()
    loading.value = false
    return
  }

  loading.value = true
  try {
    const languageExtension = await loadLanguageExtension(props.path)
    await nextTick()
    disposeEditor()

    if (!mountEl.value) return

    const state = EditorState.create({
      doc: props.content || '',
      extensions: [
        basicSetup,
        editorTheme(),
        EditorView.updateListener.of((update) => {
          if (!update.docChanged) return
          const nextValue = update.state.doc.toString()
          if (nextValue !== props.content) {
            emit('update:content', nextValue)
          }
        }),
        EditorView.editable.of(true),
        languageExtension,
      ],
    })

    editorView.value = new EditorView({
      state,
      parent: mountEl.value,
    })
  } finally {
    loading.value = false
  }
}

function syncContent() {
  if (!editorView.value) return
  const currentValue = editorView.value.state.doc.toString()
  if (currentValue === props.content) return
  editorView.value.dispatch({
    changes: {
      from: 0,
      to: currentValue.length,
      insert: props.content || '',
    },
  })
}

watch(
  () => props.path,
  () => {
    void renderEditor()
  },
  { immediate: true },
)

onMounted(() => {
  void renderEditor()
})

watch(
  () => props.content,
  () => {
    syncContent()
  },
)

onBeforeUnmount(() => {
  disposeEditor()
})
</script>

<style scoped>
.editorShell {
  width: 100%;
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.editorToolbar {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 0 0 12px;
}

.fileMeta {
  min-width: 0;
}

.filePath {
  font-size: 15px;
  font-weight: 900;
  color: rgba(31, 35, 41, 0.9);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fileInfo {
  margin-top: 4px;
  font-size: 12px;
  color: rgba(31, 35, 41, 0.56);
}

.dirtyFlag {
  color: #d97706;
  font-weight: 700;
}

.toolbarActions {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.actionBtn {
  height: 30px;
}
.fontSelect {
  width: 110px;
}

.editorMount {
  position: relative;
  flex: 1;
  min-height: 0;
  min-width: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
  border-radius: 16px;
  border: 1px solid rgba(31, 35, 41, 0.08);
  background: #fff;
}

.emptyState {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: rgba(31, 35, 41, 0.58);
  font-size: 13px;
}

.editorMount :deep() {
  width: 100%;
  height: 100%;
  overflow: auto;
}
</style>
