<template>
  <div class="markdownBody" v-html="renderedHtml"></div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  content: string
}>()

type Block =
  | { type: 'heading'; level: number; text: string }
  | { type: 'paragraph'; text: string }
  | { type: 'list'; ordered: boolean; items: string[] }
  | { type: 'table'; headers: string[]; aligns: Array<'left' | 'center' | 'right'>; rows: string[][] }
  | { type: 'code'; code: string }

function escapeHtml(input: string) {
  return input
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

function renderInlineMarkdown(input: string) {
  let html = escapeHtml(input)
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>')
  html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>')
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>')
  return html
}

function normalizeSource(source: string) {
  return String(source || '')
    .replace(/\r\n/g, '\n')
    .replace(/<br\s*\/?>/gi, '\n')
}

function splitTableRow(line: string) {
  const normalized = line.trim().replace(/^\|/, '').replace(/\|$/, '')
  return normalized.split('|').map((cell) => cell.trim())
}

function parseTableAligns(line: string) {
  const cells = splitTableRow(line)
  const aligns: Array<'left' | 'center' | 'right'> = []
  for (const cell of cells) {
    if (!/^:?-{3,}:?$/.test(cell.replace(/\s+/g, ''))) return null
    const compact = cell.replace(/\s+/g, '')
    if (compact.startsWith(':') && compact.endsWith(':')) aligns.push('center')
    else if (compact.endsWith(':')) aligns.push('right')
    else aligns.push('left')
  }
  return aligns
}

function parseBlocks(source: string): Block[] {
  const lines = normalizeSource(source).split('\n')
  const blocks: Block[] = []
  let index = 0

  while (index < lines.length) {
    const line = lines[index] ?? ''
    const trimmed = line.trim()

    if (!trimmed) {
      index += 1
      continue
    }

    if (trimmed.startsWith('```')) {
      const codeLines: string[] = []
      index += 1
      while (index < lines.length && !(lines[index] ?? '').trim().startsWith('```')) {
        codeLines.push(lines[index] ?? '')
        index += 1
      }
      if (index < lines.length) index += 1
      blocks.push({ type: 'code', code: codeLines.join('\n') })
      continue
    }

    const heading = trimmed.match(/^(#{1,6})\s+(.*)$/)
    if (heading) {
      blocks.push({
        type: 'heading',
        level: (heading[1] || '').length,
        text: heading[2] ?? '',
      })
      index += 1
      continue
    }

    const nextTrimmed = (lines[index + 1] ?? '').trim()
    if (trimmed.includes('|') && nextTrimmed.includes('|')) {
      const aligns = parseTableAligns(nextTrimmed)
      if (aligns) {
        const headers = splitTableRow(trimmed)
        const rows: string[][] = []
        index += 2
        while (index < lines.length) {
          const currentTrimmed = (lines[index] ?? '').trim()
          if (!currentTrimmed || !currentTrimmed.includes('|')) break
          rows.push(splitTableRow(currentTrimmed))
          index += 1
        }
        blocks.push({ type: 'table', headers, aligns, rows })
        continue
      }
    }

    const unordered = trimmed.match(/^[-*]\s+(.*)$/)
    const ordered = trimmed.match(/^\d+\.\s+(.*)$/)
    if (unordered || ordered) {
      const orderedList = Boolean(ordered)
      const items: string[] = []
      while (index < lines.length) {
        const current = (lines[index] ?? '').trim()
        const match = orderedList
          ? current.match(/^\d+\.\s+(.*)$/)
          : current.match(/^[-*]\s+(.*)$/)
        if (!match) break
        items.push(match[1] ?? '')
        index += 1
      }
      blocks.push({ type: 'list', ordered: orderedList, items })
      continue
    }

    const paragraphLines: string[] = []
    while (index < lines.length) {
      const current = lines[index] ?? ''
      const currentTrimmed = current.trim()
      if (!currentTrimmed) break
      if (currentTrimmed.startsWith('```')) break
      if (/^(#{1,6})\s+/.test(currentTrimmed)) break
      if (/^[-*]\s+/.test(currentTrimmed)) break
      if (/^\d+\.\s+/.test(currentTrimmed)) break
      paragraphLines.push(currentTrimmed)
      index += 1
    }
    blocks.push({ type: 'paragraph', text: paragraphLines.join('<br />') })
  }

  return blocks
}

function renderBlocks(source: string) {
  return parseBlocks(source)
    .map((block) => {
      if (block.type === 'heading') {
        const level = Math.min(Math.max(block.level, 1), 6)
        return `<h${level}>${renderInlineMarkdown(block.text)}</h${level}>`
      }
      if (block.type === 'code') {
        return `<pre><code>${escapeHtml(block.code)}</code></pre>`
      }
      if (block.type === 'list') {
        const tag = block.ordered ? 'ol' : 'ul'
        const items = block.items.map((item) => `<li>${renderInlineMarkdown(item)}</li>`).join('')
        return `<${tag}>${items}</${tag}>`
      }
      if (block.type === 'table') {
        const headerHtml = block.headers
          .map((cell, idx) => `<th class="align-${block.aligns[idx] || 'left'}">${renderInlineMarkdown(cell)}</th>`)
          .join('')
        const bodyHtml = block.rows
          .map(
            (row) =>
              `<tr>${row
                .map((cell, idx) => `<td class="align-${block.aligns[idx] || 'left'}">${renderInlineMarkdown(cell)}</td>`)
                .join('')}</tr>`,
          )
          .join('')
        return `<div class="mdTableWrap"><table><thead><tr>${headerHtml}</tr></thead><tbody>${bodyHtml}</tbody></table></div>`
      }
      return `<p>${renderInlineMarkdown(block.text)}</p>`
    })
    .join('')
}

const renderedHtml = computed(() => renderBlocks(props.content))
</script>

<style scoped>
.markdownBody {
  color: inherit;
}
.markdownBody :deep(*) {
  margin: 0;
}
.markdownBody :deep(h1),
.markdownBody :deep(h2),
.markdownBody :deep(h3),
.markdownBody :deep(h4),
.markdownBody :deep(h5),
.markdownBody :deep(h6) {
  font-size: inherit;
  line-height: 1.4;
  font-weight: 800;
}
.markdownBody :deep(p + p),
.markdownBody :deep(p + ul),
.markdownBody :deep(p + ol),
.markdownBody :deep(ul + p),
.markdownBody :deep(ol + p),
.markdownBody :deep(pre + p),
.markdownBody :deep(p + pre),
.markdownBody :deep(ul + ul),
.markdownBody :deep(ol + ol) {
  margin-top: 8px;
}
.markdownBody :deep(.mdTableWrap) {
  overflow-x: auto;
  margin-top: 8px;
}
.markdownBody :deep(table) {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.96em;
}
.markdownBody :deep(th),
.markdownBody :deep(td) {
  padding: 8px 10px;
  border: 1px solid rgba(31, 35, 41, 0.12);
  vertical-align: top;
}
.markdownBody :deep(th) {
  font-weight: 700;
  background: rgba(31, 35, 41, 0.05);
}
.markdownBody :deep(.align-left) {
  text-align: left;
}
.markdownBody :deep(.align-center) {
  text-align: center;
}
.markdownBody :deep(.align-right) {
  text-align: right;
}
.markdownBody :deep(ul),
.markdownBody :deep(ol) {
  padding-left: 20px;
}
.markdownBody :deep(li + li) {
  margin-top: 4px;
}
.markdownBody :deep(code) {
  padding: 0.1em 0.35em;
  border-radius: 6px;
  background: rgba(31, 35, 41, 0.08);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.92em;
}
.markdownBody :deep(pre) {
  overflow: auto;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(31, 35, 41, 0.06);
}
.markdownBody :deep(pre code) {
  padding: 0;
  background: transparent;
}
.markdownBody :deep(a) {
  color: #2f6fed;
  text-decoration: none;
}
.markdownBody :deep(a:hover) {
  text-decoration: underline;
}
</style>
