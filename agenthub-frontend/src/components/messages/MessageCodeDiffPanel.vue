<template>
  <div class="sidePanel">
    <div class="sideHeader">
      <div>
        <div class="sideTitle">代码 Diff</div>
        <div class="sideSubtitle">{{ activeGroup?.name || '未选择会话' }}</div>
      </div>
      <button class="sideCloseBtn" type="button" aria-label="关闭代码 Diff 面板" @click="$emit('close')">
        ×
      </button>
    </div>

    <div class="sideBody">
      <div v-if="loading" class="empty">加载中…</div>
      <div v-else-if="error" class="errBox">{{ error }}</div>
      <div v-else-if="!diff" class="empty">暂无 Diff 数据</div>
      <div v-else-if="diff.status === 'failed'" class="errBox">{{ diff.error || '代码 Diff 不可用' }}</div>
      <div v-else-if="diff.status === 'unavailable'" class="empty">当前消息没有可用的代码 Diff</div>
      <div v-else class="diffShell">
        <div class="panelCard">
          <div class="sectionTitle">变更摘要</div>
          <div class="statusRow">
            <span class="statusLabel">状态</span>
            <span class="statusValue">{{ diff.status === 'no_changes' ? '无代码变更' : '已生成' }}</span>
          </div>
          <div class="statusRow">
            <span class="statusLabel">文件数</span>
            <span class="statusValue">{{ diff.summary?.changed_file_count ?? 0 }}</span>
          </div>
          <div class="statusRow">
            <span class="statusLabel">新增行</span>
            <span class="statusValue">{{ diff.summary?.insertions ?? 0 }}</span>
          </div>
          <div class="statusRow">
            <span class="statusLabel">删除行</span>
            <span class="statusValue">{{ diff.summary?.deletions ?? 0 }}</span>
          </div>
          <div class="statusRow">
            <span class="statusLabel">提交范围</span>
            <span class="mono">{{ commitRange }}</span>
          </div>
        </div>

        <div v-if="diff.status === 'no_changes'" class="panelCard">
          <div class="empty">这条对话没有带来实际代码变更。</div>
        </div>

        <template v-else>
          <div class="panelCard">
            <div class="sectionTitle">文件列表</div>
            <div v-if="diff.files.length === 0" class="empty">暂无文件明细</div>
            <button
              v-for="file in diff.files"
              :key="`${file.old_path || ''}:${file.path}`"
              type="button"
              class="fileItem"
              :class="[fileToneClass(file), { active: activeFileKey === fileKey(file) }]"
              @click="activeFileKey = fileKey(file)"
            >
              <span class="filePath">{{ file.path }}</span>
              <span class="fileMeta">{{ file.change_type }} · +{{ file.additions }} -{{ file.deletions }}</span>
            </button>
          </div>

          <div class="panelCard">
            <div class="sectionTitle">文件 Diff</div>
            <div v-if="!activeFile" class="empty">选择一个文件查看 Diff</div>
            <template v-else>
              <div class="statusRow">
                <span class="statusLabel">文件</span>
                <span class="mono">{{ activeFile.path }}</span>
              </div>
              <div class="statusRow">
                <span class="statusLabel">变更类型</span>
                <span class="statusValue">{{ activeFile.change_type }}</span>
              </div>
              <div v-if="activeFile.old_path" class="statusRow">
                <span class="statusLabel">原路径</span>
                <span class="mono">{{ activeFile.old_path }}</span>
              </div>
              <div v-if="parsedActiveFile && parsedActiveFile.lines.length > 0" class="diffViewerWrap">
                <div class="diffViewer">
                  <div
                    v-for="(line, index) in parsedActiveFile.lines"
                    :key="`${line.kind}:${index}:${line.text}`"
                    class="diffLine"
                    :class="`is-${line.kind}`"
                  >
                    <div class="lineNo old">{{ line.oldLineNumber ?? '' }}</div>
                    <div class="lineNo new">{{ line.newLineNumber ?? '' }}</div>
                    <div class="lineCode">{{ line.text }}</div>
                  </div>
                </div>
              </div>
              <div v-else class="empty">该文件为二进制或无可展示补丁。</div>
            </template>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Group } from '../../api/groups'
import type { MessageCodeDiffFile, MessageCodeDiffResponse } from '../../api/messages'

type ParsedDiffLineKind = 'file_header' | 'hunk_header' | 'context' | 'added' | 'removed' | 'meta'

type ParsedDiffLine = {
  kind: ParsedDiffLineKind
  text: string
  oldLineNumber: number | null
  newLineNumber: number | null
}

type ParsedDiffFileView = {
  lines: ParsedDiffLine[]
}

const props = defineProps<{
  activeGroup: Group | null
  loading: boolean
  diff: MessageCodeDiffResponse | null
  error: string
}>()

defineEmits<{
  (e: 'close'): void
}>()

const activeFileKey = ref('')

function fileKey(file: MessageCodeDiffFile) {
  return `${file.old_path || ''}:${file.path}`
}

const activeFile = computed(() => {
  if (!props.diff?.files?.length) return null
  const first = props.diff.files[0]
  if (!activeFileKey.value) return first
  return props.diff.files.find((item) => fileKey(item) === activeFileKey.value) || first
})

const parsedActiveFile = computed<ParsedDiffFileView | null>(() => {
  if (!activeFile.value?.patch || activeFile.value.change_type === 'binary') return null
  return parseUnifiedDiff(activeFile.value)
})

const commitRange = computed(() => {
  const before = props.diff?.summary?.before_commit || '-'
  const after = props.diff?.summary?.after_commit || '-'
  return `${before}..${after}`
})

function fileToneClass(file: MessageCodeDiffFile) {
  if (file.change_type === 'added') return 'is-added'
  if (file.change_type === 'deleted') return 'is-deleted'
  if (file.change_type === 'renamed') return 'is-renamed'
  return 'is-modified'
}

function parseUnifiedDiff(file: MessageCodeDiffFile): ParsedDiffFileView {
  const patch = String(file.patch || '')
  const lines = patch.split('\n')
  const parsed: ParsedDiffLine[] = []
  let oldLineNumber: number | null = null
  let newLineNumber: number | null = null

  for (const rawLine of lines) {
    if (rawLine === '' && parsed.length > 0 && parsed.at(-1)?.text === '') {
      continue
    }
    if (rawLine.startsWith('@@')) {
      const headerMatch = rawLine.match(/^@@\s+\-(\d+)(?:,\d+)?\s+\+(\d+)(?:,\d+)?\s+@@/)
      oldLineNumber = headerMatch ? Number(headerMatch[1]) : null
      newLineNumber = headerMatch ? Number(headerMatch[2]) : null
      parsed.push({
        kind: 'hunk_header',
        text: rawLine,
        oldLineNumber: null,
        newLineNumber: null,
      })
      continue
    }

    if (rawLine.startsWith('--- ') || rawLine.startsWith('+++ ')) {
      parsed.push({
        kind: 'file_header',
        text: rawLine,
        oldLineNumber: null,
        newLineNumber: null,
      })
      continue
    }

    if (rawLine.startsWith('+') && !rawLine.startsWith('+++')) {
      parsed.push({
        kind: 'added',
        text: rawLine,
        oldLineNumber: null,
        newLineNumber,
      })
      newLineNumber = newLineNumber == null ? null : newLineNumber + 1
      continue
    }

    if (rawLine.startsWith('-') && !rawLine.startsWith('---')) {
      parsed.push({
        kind: 'removed',
        text: rawLine,
        oldLineNumber,
        newLineNumber: null,
      })
      oldLineNumber = oldLineNumber == null ? null : oldLineNumber + 1
      continue
    }

    if (rawLine.startsWith(' ')) {
      parsed.push({
        kind: 'context',
        text: rawLine,
        oldLineNumber,
        newLineNumber,
      })
      oldLineNumber = oldLineNumber == null ? null : oldLineNumber + 1
      newLineNumber = newLineNumber == null ? null : newLineNumber + 1
      continue
    }

    parsed.push({
      kind: 'meta',
      text: rawLine,
      oldLineNumber: null,
      newLineNumber: null,
    })
  }

  return { lines: parsed }
}

watch(
  () => props.diff?.files,
  (files) => {
    if (!files || files.length === 0) {
      activeFileKey.value = ''
      return
    }
    activeFileKey.value = fileKey(files[0]!)
  },
  { immediate: true },
)
</script>

<style scoped>
.sidePanel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.84);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 18px;
}
.sideHeader {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 18px 14px;
  border-bottom: 1px solid rgba(31, 35, 41, 0.08);
}
.sideTitle {
  font-size: 18px;
  font-weight: 700;
}
.sideSubtitle {
  margin-top: 4px;
  font-size: 12px;
  color: rgba(31, 35, 41, 0.6);
}
.sideCloseBtn {
  border: 0;
  background: transparent;
  font-size: 22px;
  cursor: pointer;
}
.sideBody {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 16px;
}
.diffShell {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.panelCard {
  border: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 14px;
  padding: 14px;
  background: rgba(255, 255, 255, 0.9);
}
.sectionTitle {
  font-size: 14px;
  font-weight: 700;
  margin-bottom: 10px;
}
.statusRow {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-top: 8px;
}
.statusLabel {
  color: rgba(31, 35, 41, 0.6);
}
.statusValue,
.mono {
  text-align: right;
  word-break: break-all;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.fileItem {
  width: 100%;
  text-align: left;
  border: 1px solid rgba(31, 35, 41, 0.08);
  background: rgba(31, 35, 41, 0.02);
  border-radius: 12px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  cursor: pointer;
  margin-top: 8px;
}
.fileItem.active {
  border-color: rgba(79, 140, 255, 0.36);
  background: rgba(79, 140, 255, 0.08);
}
.fileItem.is-added {
  border-left: 3px solid rgba(34, 197, 94, 0.72);
}
.fileItem.is-deleted {
  border-left: 3px solid rgba(239, 68, 68, 0.72);
}
.fileItem.is-renamed {
  border-left: 3px solid rgba(245, 158, 11, 0.72);
}
.fileItem.is-modified {
  border-left: 3px solid rgba(59, 130, 246, 0.6);
}
.filePath {
  font-weight: 600;
}
.fileMeta {
  font-size: 12px;
  color: rgba(31, 35, 41, 0.6);
}
.diffViewerWrap {
  margin-top: 12px;
  overflow: auto;
  border: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 12px;
  background: rgba(248, 250, 252, 0.92);
}
.diffViewer {
  min-width: max-content;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.diffLine {
  display: grid;
  grid-template-columns: 64px 64px minmax(0, 1fr);
  align-items: stretch;
}
.lineNo {
  padding: 6px 8px;
  text-align: right;
  color: rgba(31, 35, 41, 0.42);
  border-right: 1px solid rgba(31, 35, 41, 0.06);
  user-select: none;
}
.lineCode {
  padding: 6px 12px;
  white-space: pre;
}
.diffLine.is-context .lineCode {
  background: rgba(255, 255, 255, 0.92);
  color: rgba(15, 23, 42, 0.88);
}
.diffLine.is-added .lineCode,
.diffLine.is-added .lineNo {
  background: rgba(34, 197, 94, 0.12);
  color: #166534;
}
.diffLine.is-added .lineCode {
  box-shadow: inset 3px 0 0 rgba(34, 197, 94, 0.55);
}
.diffLine.is-removed .lineCode,
.diffLine.is-removed .lineNo {
  background: rgba(239, 68, 68, 0.12);
  color: #991b1b;
}
.diffLine.is-removed .lineCode {
  box-shadow: inset 3px 0 0 rgba(239, 68, 68, 0.52);
}
.diffLine.is-hunk_header .lineCode,
.diffLine.is-hunk_header .lineNo {
  background: rgba(59, 130, 246, 0.08);
  color: #365b87;
}
.diffLine.is-file_header .lineCode,
.diffLine.is-file_header .lineNo,
.diffLine.is-meta .lineCode,
.diffLine.is-meta .lineNo {
  background: rgba(15, 23, 42, 0.04);
  color: rgba(51, 65, 85, 0.74);
}
.diffLine.is-meta .lineCode {
  font-style: italic;
}
.diffLine + .diffLine {
  border-top: 1px solid rgba(31, 35, 41, 0.04);
}
.lineNo.old {
  border-right: 1px solid rgba(31, 35, 41, 0.04);
}
.lineNo.new {
  border-right: 1px solid rgba(31, 35, 41, 0.08);
}
.lineCode,
.lineNo {
  font-size: 12px;
  line-height: 1.5;
}
.errBox {
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(220, 38, 38, 0.08);
  color: #b91c1c;
}
.empty {
  color: rgba(31, 35, 41, 0.6);
}
</style>
