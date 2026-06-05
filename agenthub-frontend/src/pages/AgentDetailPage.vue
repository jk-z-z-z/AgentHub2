<template>
  <div class="shell">
    <div class="header">
      <div class="title">智能体详情：{{ agent?.display_name || agentId }}</div>
      <div class="actions">
        <el-button @click="router.push('/agents')">返回管理</el-button>
        <el-button @click="reloadAll" :disabled="!agentId || saving">刷新</el-button>
        <el-button
          type="primary"
          @click="save"
          :loading="saving"
          :disabled="!agentId || !activeFilePath"
          >保存</el-button
        >
      </div>
    </div>

    <div class="body">
      <section class="panel">
        <div class="panelInner">
          <aside class="files">
            <div class="filesTitle">文件</div>
            <div v-if="loading" class="hint">加载中…</div>
            <el-input
              v-model="filter"
              placeholder="搜索文件…"
              size="small"
              style="margin: 6px 0 10px 0"
            />

            <div class="tree">
              <AgentFileTreeNode
                v-for="n in treeRoots"
                :key="n.path"
                :node="n"
                :active-path="activeFilePath"
                :open-dirs="openDirs"
                @open="openFile"
                @toggle="toggleDir"
              />
            </div>

            <div class="ops">
              <el-select v-model="newFileDir" style="width: 140px">
                <el-option label="skills/" value="skills/" />
                <el-option label="knowledge/" value="knowledge/" />
                <el-option label="mcps/" value="mcps/" />
              </el-select>
              <el-input v-model="newFilePath" placeholder="例如：web/search.md 或 notes.md" />
              <el-button type="primary" @click="createFile" :disabled="!newFilePath.trim()"
                >新建</el-button
              >
            </div>
          </aside>

          <main class="editor">
            <div class="editorHeader">
              <div class="editorTitle">{{ activeFilePath || '选择一个文件' }}</div>
              <div class="editorActions">
                <el-button
                  size="small"
                  type="danger"
                  plain
                  @click="removeFile"
                  :disabled="!canDeleteActive"
                >
                  删除
                </el-button>
              </div>
            </div>
            <div class="editorBody">
              <div class="toolPanel">
                <div class="toolTitle">工具启用</div>
                <div class="toolHint">工具为内置能力；智能体仅配置是否启用。</div>
                <el-table :data="tools" size="small" empty-text="暂无内置工具" class="toolList" height="240">
                  <el-table-column label="工具" min-width="220">
                    <template #default="{ row }">
                      <div class="tName">{{ row.name }}</div>
                      <div class="tMeta">{{ row.code }} · {{ row.source_type }}</div>
                    </template>
                  </el-table-column>
                  <el-table-column label="启用" width="100" align="right">
                    <template #default="{ row }">
                      <el-switch v-model="toolToggles[row.code]" />
                    </template>
                  </el-table-column>
                </el-table>
                <div class="toolActions">
                  <el-button size="small" :loading="toolSaving" @click="saveToolToggles"
                    >保存工具开关</el-button
                  >
                </div>
              </div>

              <div class="toolPanel">
                <div class="toolTitle">技能加载</div>
                <div class="toolHint">
                  可从全局 Skill 池选择，也可控制是否加载该 Agent 本地 skills 目录。
                </div>
                <div class="toolRow">
                  <div class="tLeft">
                    <div class="tName">加载本地 skills/</div>
                    <div class="tMeta">开启后会递归加载该智能体目录下的 SKILL.md</div>
                  </div>
                  <div class="tRight">
                    <el-switch v-model="skillConfig.enable_agent_local_skills" />
                  </div>
                </div>
                <el-table :data="skillPool" size="small" empty-text="全局 Skill 池为空（请在后端 skill-pool 目录下放置 SKILL.md）" class="toolList" height="240">
                  <el-table-column label="技能" min-width="220">
                    <template #default="{ row }">
                      <div class="tName">{{ row.name || row.code }}</div>
                      <div class="tMeta">{{ row.code }} · {{ row.description || '无描述' }}</div>
                    </template>
                  </el-table-column>
                  <el-table-column label="选择" width="100" align="right">
                    <template #default="{ row }">
                      <el-checkbox
                        :model-value="skillConfig.pool_skill_codes.includes(row.code)"
                        @change="(v: boolean) => togglePoolSkill(row.code, v)"
                      />
                    </template>
                  </el-table-column>
                </el-table>
                <div class="toolActions">
                  <el-button size="small" :loading="skillSaving" @click="saveSkillConfig"
                    >保存技能配置</el-button
                  >
                </div>
              </div>

              <div v-if="!activeFilePath" class="hint">从左侧选择文件</div>
              <el-input
                v-else
                v-model="content"
                type="textarea"
                :rows="20"
                placeholder="编辑内容"
              />
              <div v-if="err" class="err">{{ err }}</div>
            </div>
          </main>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  apiDeleteAgentFsFile,
  apiGetAgentSkillConfig,
  apiGetAgentToolToggles,
  apiListAgentFs,
  apiListAgentSkillPool,
  apiListAgents,
  apiListTools,
  apiReadAgentFsFile,
  apiUpdateAgentSkillConfig,
  apiUpdateAgentToolToggles,
  apiWriteAgentFsFile,
  type Agent,
  type FsEntry,
  type SkillPoolItem,
  type Tool,
} from '../api/agents'
import { ElMessage } from 'element-plus'
import AgentFileTreeNode, { type FileTreeNode } from '../components/AgentFileTreeNode.vue'

const route = useRoute()
const router = useRouter()

const agentId = computed(() => String(route.params.id || ''))
const agent = ref<Agent | null>(null)

const files = ref<FsEntry[]>([])
const loading = ref(false)
const activeFilePath = ref('')
const content = ref('')
const saving = ref(false)
const err = ref('')

const tools = ref<Tool[]>([])
const toolToggles = ref<Record<string, boolean>>({})
const toolSaving = ref(false)
const skillPool = ref<SkillPoolItem[]>([])
const skillConfig = ref<{ enable_agent_local_skills: boolean; pool_skill_codes: string[] }>({
  enable_agent_local_skills: true,
  pool_skill_codes: [],
})
const skillSaving = ref(false)

const newFileDir = ref<'skills/' | 'knowledge/' | 'mcps/'>('skills/')
const newFilePath = ref('')
const filter = ref('')
const openDirs = ref<Record<string, boolean>>({
  'core/': true,
  'skills/': true,
  'knowledge/': true,
  'mcps/': true,
})

const filteredFiles = computed(() => {
  const q = filter.value.trim().toLowerCase()
  if (!q) return files.value
  return files.value.filter((f) => f.path.toLowerCase().includes(q))
})

function splitPath(p: string) {
  const clean = p.replace(/\\/g, '/').replace(/^\/+/, '')
  return clean.split('/').filter(Boolean)
}

function buildTree(entries: FsEntry[]): FileTreeNode[] {
  const nodes = new Map<string, FileTreeNode>()
  const ensure = (path: string, is_dir: boolean, size: number): FileTreeNode => {
    if (nodes.has(path)) return nodes.get(path)!
    const parts = splitPath(path)
    const last = parts.slice(-1)[0] || path.replace(/\/+$/, '')
    const label = path.endsWith('/') ? `${last}/` : last
    const n: FileTreeNode = { path, label, is_dir, size, children: [] }
    nodes.set(path, n)
    return n
  }
  const addChild = (parent: FileTreeNode, child: FileTreeNode) => {
    if (!parent.children.some((c) => c.path === child.path)) parent.children.push(child)
  }

  const core = ensure('core/', true, 0)
  const skills = ensure('skills/', true, 0)
  const knowledge = ensure('knowledge/', true, 0)
  const mcps = ensure('mcps/', true, 0)

  for (const e of entries) {
    const raw = e.path
    if (!raw) continue
    const isDir = e.is_dir || raw.endsWith('/')
    if (
      raw === 'SOUL.md' ||
      raw === 'PROFILE.md' ||
      raw === 'BOOTSTRAP.md' ||
      raw === 'MEMORY.md' ||
      raw === 'tools.json' ||
      raw === 'skills.json' ||
      raw === 'profile.enabled_files.json'
    ) {
      addChild(core, ensure(`core/${raw}`, false, e.size || 0))
      continue
    }
    const parts = splitPath(raw)
    const top = parts[0]
    if (top !== 'skills' && top !== 'knowledge' && top !== 'mcps') continue
    let parent = top === 'skills' ? skills : top === 'knowledge' ? knowledge : mcps
    for (let i = 1; i < parts.length; i++) {
      const isLast = i === parts.length - 1
      const p = `${parts.slice(0, i + 1).join('/')}${isLast && isDir ? '/' : ''}`
      const node = ensure(p, isLast ? isDir : true, isLast ? (isDir ? 0 : e.size || 0) : 0)
      addChild(parent, node)
      parent = node
    }
  }

  const sortNode = (n: FileTreeNode) => {
    n.children.sort((a, b) => {
      if (a.is_dir !== b.is_dir) return a.is_dir ? -1 : 1
      return a.label.localeCompare(b.label)
    })
    n.children.forEach(sortNode)
  }
  ;[core, skills, knowledge, mcps].forEach(sortNode)
  return [core, skills, knowledge, mcps]
}

const treeRoots = computed(() => buildTree(filteredFiles.value))

async function loadAgentMeta() {
  const res = await apiListAgents()
  agent.value = res.data.find((a) => String(a.id) === agentId.value) || null
}

async function loadTools() {
  const res = await apiListTools()
  tools.value = res.data
}

async function loadToolToggles() {
  if (!agentId.value) return
  const res = await apiGetAgentToolToggles(agentId.value)
  toolToggles.value = res.data.enabled || {}
}

async function loadSkillPool() {
  const res = await apiListAgentSkillPool()
  skillPool.value = res.data || []
}

async function loadSkillConfig() {
  if (!agentId.value) return
  const res = await apiGetAgentSkillConfig(agentId.value)
  skillConfig.value = {
    enable_agent_local_skills: res.data.enable_agent_local_skills,
    pool_skill_codes: Array.isArray(res.data.pool_skill_codes)
      ? [...res.data.pool_skill_codes]
      : [],
  }
}

async function reloadAll() {
  err.value = ''
  if (!agentId.value) return
  try {
    loading.value = true
    await Promise.all([loadToolToggles(), loadTools(), loadSkillPool(), loadSkillConfig()])
    const res = await apiListAgentFs(agentId.value)
    files.value = res.data.filter((x) => !x.path.endsWith('/'))
    if (!activeFilePath.value) {
      const prefer = ['SOUL.md', 'PROFILE.md']
      const first =
        prefer.find((p) => files.value.some((f) => f.path === p)) || files.value[0]?.path
      if (first) await openFile(first)
    } else {
      await openFile(activeFilePath.value)
    }
  } catch (e) {
    err.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

function togglePoolSkill(code: string, checked: boolean) {
  const s = new Set(skillConfig.value.pool_skill_codes)
  if (checked) s.add(code)
  else s.delete(code)
  skillConfig.value.pool_skill_codes = Array.from(s)
}

async function saveSkillConfig() {
  if (!agentId.value) return
  skillSaving.value = true
  try {
    const payload = {
      enable_agent_local_skills: !!skillConfig.value.enable_agent_local_skills,
      pool_skill_codes: Array.from(new Set(skillConfig.value.pool_skill_codes)),
    }
    await apiUpdateAgentSkillConfig(agentId.value, payload)
    ElMessage.success('已保存技能配置')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : String(e))
  } finally {
    skillSaving.value = false
  }
}

async function saveToolToggles() {
  if (!agentId.value) return
  toolSaving.value = true
  try {
    await apiUpdateAgentToolToggles(agentId.value, toolToggles.value)
    ElMessage.success('已保存工具开关')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : String(e))
  } finally {
    toolSaving.value = false
  }
}

async function openFile(path: string) {
  err.value = ''
  if (!agentId.value) return
  activeFilePath.value = path
  try {
    const actual = path.startsWith('core/') ? path.replace(/^core\//, '') : path
    const res = await apiReadAgentFsFile(agentId.value, actual)
    content.value = res.data.content || ''
  } catch (e) {
    err.value = e instanceof Error ? e.message : String(e)
  }
}

async function save() {
  err.value = ''
  if (!agentId.value) return
  if (!activeFilePath.value) return
  saving.value = true
  try {
    const actual = activeFilePath.value.startsWith('core/')
      ? activeFilePath.value.replace(/^core\//, '')
      : activeFilePath.value
    await apiWriteAgentFsFile(agentId.value, actual, content.value)
  } catch (e) {
    err.value = e instanceof Error ? e.message : String(e)
  } finally {
    saving.value = false
  }
}

const canDeleteActive = computed(() => {
  const p = activeFilePath.value
  if (!p) return false
  const actual = p.startsWith('core/') ? p.replace(/^core\//, '') : p
  if (actual === 'SOUL.md' || actual === 'PROFILE.md') return false
  return (
    actual.startsWith('skills/') || actual.startsWith('knowledge/') || actual.startsWith('mcps/')
  )
})

async function createFile() {
  err.value = ''
  if (!agentId.value) return
  const rel = newFilePath.value.trim().replace(/\\/g, '/').replace(/^\/+/, '')
  if (!rel) return
  if (rel.includes('..')) {
    err.value = '路径不能包含 ..'
    return
  }
  const path = `${newFileDir.value}${rel}`
  try {
    await apiWriteAgentFsFile(agentId.value, path, '')
    newFilePath.value = ''
    await reloadAll()
    await openFile(path)
  } catch (e) {
    err.value = e instanceof Error ? e.message : String(e)
  }
}

async function removeFile() {
  err.value = ''
  if (!agentId.value) return
  if (!canDeleteActive.value) return
  const actual = activeFilePath.value.startsWith('core/')
    ? activeFilePath.value.replace(/^core\//, '')
    : activeFilePath.value
  try {
    await apiDeleteAgentFsFile(agentId.value, actual)
    activeFilePath.value = ''
    content.value = ''
    await reloadAll()
  } catch (e) {
    err.value = e instanceof Error ? e.message : String(e)
  }
}

function toggleDir(path: string) {
  openDirs.value = { ...openDirs.value, [path]: !openDirs.value[path] }
}

onMounted(async () => {
  await Promise.all([loadAgentMeta(), reloadAll()])
})
</script>

<style scoped>
.shell {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.header {
  height: 64px;
  padding: 0 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.title {
  font-weight: 900;
  font-size: 16px;
}
.actions {
  display: flex;
  gap: 10px;
}
.body {
  flex: 1;
  min-height: 0;
}
.panel {
  height: 100%;
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(12px);
  border-radius: 18px;
  overflow: hidden;
  padding: 14px;
}
.panelInner {
  height: 100%;
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 14px;
  min-height: 0;
}
.files {
  border: 1px solid rgba(31, 35, 41, 0.06);
  border-radius: 16px;
  overflow: auto;
  padding: 10px;
  min-height: 0;
}
.filesTitle {
  font-weight: 900;
  margin-bottom: 8px;
}
.tree {
  display: grid;
  gap: 4px;
}
.editor {
  border: 1px solid rgba(31, 35, 41, 0.06);
  border-radius: 16px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.editorHeader {
  height: 52px;
  border-bottom: 1px solid rgba(31, 35, 41, 0.06);
  display: flex;
  align-items: center;
  padding: 0 12px;
  justify-content: space-between;
}
.editorTitle {
  font-weight: 900;
}
.editorActions {
  display: flex;
  gap: 8px;
}
.editorBody {
  padding: 12px;
  overflow: auto;
  min-height: 0;
}
.toolPanel {
  border: 1px solid rgba(31, 35, 41, 0.06);
  border-radius: 14px;
  padding: 12px;
  margin-bottom: 12px;
  background: rgba(255, 255, 255, 0.65);
}
.toolTitle {
  font-weight: 900;
}
.toolHint {
  margin-top: 4px;
  font-size: 12px;
  opacity: 0.7;
}
.toolList {
  margin-top: 10px;
  display: grid;
  gap: 8px;
}
.toolRow {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border: 1px solid rgba(31, 35, 41, 0.06);
  border-radius: 12px;
  padding: 10px;
}
.tName {
  font-weight: 900;
}
.tMeta {
  margin-top: 2px;
  font-size: 12px;
  opacity: 0.65;
}
.toolActions {
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
}
.err {
  margin-top: 10px;
  color: #d92d20;
  font-size: 12px;
}
.hint {
  opacity: 0.6;
  padding: 6px 2px;
}
.ops {
  margin-top: 12px;
  border-top: 1px solid rgba(31, 35, 41, 0.06);
  padding-top: 10px;
  display: grid;
  grid-template-columns: 140px 1fr 80px;
  gap: 8px;
  align-items: center;
}
</style>
