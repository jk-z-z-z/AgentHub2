<template>
  <div class="shell">
    <aside class="centerNav">
      <div class="title">智能体中心</div>
      <div class="navItem" :class="{ active: section === 'instances' }" @click="section = 'instances'">
        智能体管理
      </div>
      <div class="navItem" :class="{ active: section === 'templates' }" @click="section = 'templates'">
        模版管理
      </div>
      <div class="navItem" :class="{ active: section === 'tools' }" @click="section = 'tools'">工具（全局）</div>
      <div class="navItem" :class="{ active: section === 'mcps' }" @click="section = 'mcps'">MCP（全局）</div>
      <div class="navItem" :class="{ active: section === 'skills' }" @click="section = 'skills'">技能（全局）</div>
    </aside>

    <main class="content">
      <section v-if="section === 'instances'" class="panel">
        <div class="panelHeader">
          <div class="panelTitle">智能体管理</div>
          <div class="actions">
            <el-button type="primary" @click="createAgentOpen = true">创建智能体</el-button>
          </div>
        </div>
        <div v-if="agentErr" class="err">{{ agentErr }}</div>
        <div class="list">
          <div v-for="a in agents" :key="a.id" class="row" @click="goAgent(String(a.id))">
            <div class="left">
              <div class="name">{{ a.display_name }}</div>
              <div class="meta">#{{ a.id }} · {{ a.status }}</div>
            </div>
            <div class="right">编辑 ›</div>
          </div>
          <div v-if="!loadingAgents && agents.length === 0" class="empty">暂无智能体</div>
        </div>
      </section>

      <section v-else-if="section === 'templates'" class="panel">
        <div class="panelHeader">
          <div class="panelTitle">模版管理</div>
          <div class="actions">
            <el-button @click="loadProfiles" :loading="loadingProfiles">刷新</el-button>
            <el-button type="primary" @click="createProfileOpen = true">新建模版</el-button>
          </div>
        </div>
        <div class="list">
          <div v-for="p in profiles" :key="p.id" class="row" @click="goProfile(String(p.id))">
            <div class="left">
              <div class="name">{{ p.name }}</div>
              <div class="meta">{{ p.role }} · {{ p.model_name }}</div>
            </div>
            <div class="right">在详情页编辑</div>
          </div>
          <div v-if="!loadingProfiles && profiles.length === 0" class="empty">暂无模版</div>
        </div>
      </section>

      <section v-else-if="section === 'tools'" class="panel">
        <div class="panelHeader">
          <div class="panelTitle">工具（全局）</div>
          <div class="actions">
            <el-button @click="loadTools" :loading="loadingTools">刷新</el-button>
          </div>
        </div>
        <div class="skillsToolbar">
          <el-input v-model="toolFilterName" placeholder="按名称/Code筛选" clearable />
          <div></div>
          <div class="viewToggles">
            <button class="viewBtn" :class="{ active: toolView === 'grid' }" @click="toolView = 'grid'">▦</button>
            <button class="viewBtn" :class="{ active: toolView === 'list' }" @click="toolView = 'list'">≣</button>
          </div>
        </div>

        <div v-if="toolView === 'grid'" class="skillsGrid">
          <div v-for="t in filteredTools" :key="t.id" class="skillCard">
            <div class="cardTop">
              <div class="docIcon">🧰</div>
              <div class="status">
                <span class="dot" :class="{ on: !!t.is_active }"></span>
                <span>{{ t.is_active ? '已启用' : '未启用' }}</span>
              </div>
            </div>
            <div class="cardName">
              <span class="code">{{ t.code }}</span>
              <span class="badge">{{ t.source_type }}</span>
            </div>
            <div class="cardMeta">
              <div class="kv"><span class="k">名称</span><span class="v">{{ t.name }}</span></div>
              <div class="kv"><span class="k">描述</span><span class="v">{{ t.description || '-' }}</span></div>
            </div>
            <div class="cardDesc">内置工具（不可由用户创建/编辑；由智能体决定是否启用）</div>
          </div>
          <div v-if="!loadingTools && filteredTools.length === 0" class="empty">暂无工具</div>
        </div>

        <div v-else class="list">
          <div v-for="t in filteredTools" :key="t.id" class="row">
            <div class="left">
              <div class="name">{{ t.name }}</div>
              <div class="meta">{{ t.code }} · {{ t.source_type }}</div>
            </div>
            <div class="right">内置</div>
          </div>
          <div v-if="!loadingTools && filteredTools.length === 0" class="empty">暂无工具</div>
        </div>
      </section>

      <section v-else-if="section === 'mcps'" class="panel">
        <div class="panelHeader">
          <div class="panelTitle">MCP（全局）</div>
          <div class="actions">
            <el-button @click="loadMcps" :loading="loadingMcps">刷新</el-button>
            <el-button type="primary" @click="createMcpOpen = true">新建</el-button>
          </div>
        </div>
        <div v-if="mcpErr" class="err">{{ mcpErr }}</div>
        <div class="skillsToolbar">
          <el-input v-model="mcpFilterName" placeholder="按名称/Code筛选" clearable />
          <div></div>
          <div class="viewToggles">
            <button class="viewBtn" :class="{ active: mcpView === 'grid' }" @click="mcpView = 'grid'">▦</button>
            <button class="viewBtn" :class="{ active: mcpView === 'list' }" @click="mcpView = 'list'">≣</button>
          </div>
        </div>

        <div v-if="mcpView === 'grid'" class="skillsGrid">
          <div v-for="m in filteredMcps" :key="m.id" class="skillCard clickable" @click="openMcp(m)">
            <div class="cardTop">
              <div class="docIcon">🔌</div>
              <div class="status">
                <span class="dot" :class="{ on: !!m.is_active }"></span>
                <span>{{ m.is_active ? '已启用' : '未启用' }}</span>
              </div>
            </div>
            <div class="cardName">
              <span class="code">{{ m.server_code }}</span>
              <span class="badge">自定义</span>
            </div>
            <div class="cardMeta">
              <div class="kv"><span class="k">名称</span><span class="v">{{ m.name }}</span></div>
              <div class="kv"><span class="k">描述</span><span class="v">{{ m.description || '-' }}</span></div>
            </div>
            <div class="cardDesc">点击查看/编辑</div>
          </div>
          <div v-if="!loadingMcps && filteredMcps.length === 0" class="empty">暂无 MCP</div>
        </div>

        <div v-else class="list">
          <div v-for="m in filteredMcps" :key="m.id" class="row" @click="openMcp(m)">
            <div class="left">
              <div class="name">{{ m.name }}</div>
              <div class="meta">{{ m.server_code }}</div>
            </div>
            <div class="right">编辑</div>
          </div>
          <div v-if="!loadingMcps && filteredMcps.length === 0" class="empty">暂无 MCP</div>
        </div>
      </section>

      <section v-else-if="section === 'skills'" class="panel">
        <div class="panelHeader">
          <div class="panelTitle">技能（全局）</div>
          <div class="actions">
            <el-button @click="loadSkillPool" :loading="loadingSkillPool">刷新</el-button>
          </div>
        </div>
        <div class="empty" style="margin-bottom: 10px; text-align: left">
          当前技能来源为后端配置目录（Skill Pool），前端此处只读展示；编辑请在目录中维护 `SKILL.md`。
        </div>
        <div class="skillsToolbar">
          <el-input v-model="skillFilterName" placeholder="按名称/Code筛选" clearable />
          <div></div>
          <div class="viewToggles">
            <button class="viewBtn" :class="{ active: skillView === 'grid' }" @click="skillView = 'grid'">▦</button>
            <button class="viewBtn" :class="{ active: skillView === 'list' }" @click="skillView = 'list'">≣</button>
          </div>
        </div>

        <div v-if="skillErr" class="err">{{ skillErr }}</div>
        <div v-if="skillView === 'grid'" class="skillsGrid">
          <div v-for="s in filteredSkills" :key="s.code" class="skillCard">
            <div class="cardTop">
              <div class="docIcon">📄</div>
              <div class="status">
                <span class="dot on"></span>
                <span>目录技能</span>
              </div>
            </div>
            <div class="cardName">
              <span class="code">{{ s.code }}</span>
              <span class="badge">Skill Pool</span>
            </div>
            <div class="cardMeta">
              <div class="kv"><span class="k">名称</span><span class="v">{{ s.name }}</span></div>
              <div class="kv"><span class="k">描述</span><span class="v">{{ s.description || '-' }}</span></div>
              <div class="kv"><span class="k">目录</span><span class="v">{{ s.dir }}</span></div>
            </div>
            <div class="cardDesc">在后端 Skill Pool 目录维护 `SKILL.md` 后，Agent 即可按配置加载。</div>
          </div>
          <div v-if="!loadingSkillPool && filteredSkills.length === 0" class="empty">暂无技能</div>
        </div>

        <div v-else class="list">
          <div v-for="s in filteredSkills" :key="s.code" class="row">
            <div class="left">
              <div class="name">{{ s.code }}</div>
              <div class="meta">{{ s.name }}</div>
            </div>
            <div class="right">目录技能</div>
          </div>
          <div v-if="!loadingSkillPool && filteredSkills.length === 0" class="empty">暂无技能</div>
        </div>
      </section>

      <section v-else class="panel">
        <div class="panelHeader">
          <div class="panelTitle">
            {{ section === 'tools' ? '工具（全局）' : section === 'mcps' ? 'MCP（全局）' : '技能（全局）' }}
          </div>
        </div>
        <div class="empty">该模块前端页面已预留；后续接入对应接口展示/创建。</div>
      </section>
    </main>
  </div>

  <el-dialog v-model="createProfileOpen" title="新建智能体模版" width="520px">
    <div class="formGrid">
      <el-input v-model="profileForm.name" placeholder="name" />
      <el-input v-model="profileForm.role" placeholder="role" />
      <el-input v-model="profileForm.model_name" placeholder="model_name" />
    </div>
    <div style="margin-top: 10px; font-weight: 800">SOUL.md</div>
    <el-input v-model="profileForm.soul_md" type="textarea" :rows="10" placeholder="模版 SOUL.md" />
    <div v-if="profileCreateErr" class="err" style="margin-top: 10px">{{ profileCreateErr }}</div>
    <template #footer>
      <el-button @click="createProfileOpen = false">取消</el-button>
      <el-button type="primary" :loading="creatingProfile" @click="createProfile">创建</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="createMcpOpen" title="新建 MCP" width="520px">
    <div class="formGrid">
      <el-input v-model="mcpForm.name" placeholder="name" />
      <el-input v-model="mcpForm.server_code" placeholder="server_code" />
      <el-input v-model="mcpForm.description" placeholder="description (可选)" />
    </div>
    <template #footer>
      <el-button @click="createMcpOpen = false">取消</el-button>
      <el-button type="primary" :loading="mcpCreating" @click="createMcp">创建</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="createAgentOpen" title="创建智能体" width="520px">
    <div class="formGrid" style="grid-template-columns: 1fr 1fr">
      <el-input v-model="newAgentName" placeholder="智能体名称 *" />
      <el-select v-model="newAgentProfileId" placeholder="选择模版(可选)" clearable>
        <el-option v-for="p in profiles" :key="p.id" :label="`${p.name} · ${p.role}`" :value="p.id" />
      </el-select>
    </div>
    <div class="templateHint">
      推荐：选择 `前端工程助手模版 · frontend-engineer`，会自动带入前端开发人格与规范。
    </div>
    <div v-if="agentErr" class="err" style="margin-top: 10px">{{ agentErr }}</div>
    <template #footer>
      <el-button @click="createAgentOpen = false">取消</el-button>
      <el-button type="primary" :loading="creatingAgent" @click="createAgent">创建</el-button>
    </template>
  </el-dialog>

  <!-- tools are builtin: no create/edit UI -->

  <el-drawer v-model="mcpDetailOpen" title="MCP 详情/编辑" direction="rtl" size="520px">
    <div class="drawerBody" v-if="activeMcp">
      <div class="drawerField">
        <div class="label">Name *</div>
        <el-input v-model="mcpEditForm.name" />
      </div>
      <div class="drawerField">
        <div class="label">Server Code *</div>
        <el-input v-model="mcpEditForm.server_code" />
      </div>
      <div class="drawerField">
        <div class="label">Description</div>
        <el-input v-model="mcpEditForm.description" type="textarea" :rows="3" />
      </div>
      <div class="drawerField">
        <div class="label">connection_json</div>
        <el-input v-model="mcpEditForm.connection_json" type="textarea" :rows="6" />
      </div>
      <div class="drawerField">
        <div class="label">capability_json</div>
        <el-input v-model="mcpEditForm.capability_json" type="textarea" :rows="6" />
      </div>
      <div class="drawerField">
        <div class="label">启用</div>
        <el-switch v-model="mcpEditForm.is_active" />
      </div>
      <div v-if="mcpErr" class="err" style="margin-top: 8px">{{ mcpErr }}</div>
      <div class="drawerFooter">
        <el-button type="danger" plain @click="deleteMcp" :loading="mcpDeleting">删除</el-button>
        <el-button @click="mcpDetailOpen = false">取消</el-button>
        <el-button type="primary" @click="saveMcp" :loading="mcpSaving">保存</el-button>
      </div>
    </div>
  </el-drawer>

</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  apiCreateAgent,
  apiCreateAgentProfile,
  apiCreateMcp,
  apiDeleteMcp,
  apiListAgentSkillPool,
  apiListAgentProfiles,
  apiListAgents,
  apiListMcps,
  apiListTools,
  apiUpdateMcp,
  type Agent,
  type AgentProfile,
  type MCP,
  type SkillPoolItem,
  type Tool,
} from '../api/agenthub'

const router = useRouter()

const section = ref<'instances' | 'templates' | 'tools' | 'mcps' | 'skills'>('instances')

const agents = ref<Agent[]>([])
const loadingAgents = ref(false)
const newAgentName = ref('')
const newAgentProfileId = ref<string | null>(null)
const createAgentOpen = ref(false)
const creatingAgent = ref(false)
const agentErr = ref('')

const profiles = ref<AgentProfile[]>([])
const loadingProfiles = ref(false)

const tools = ref<Tool[]>([])
const loadingTools = ref(false)
const mcps = ref<MCP[]>([])
const loadingMcps = ref(false)
const skills = ref<SkillPoolItem[]>([])
const loadingSkillPool = ref(false)

const createMcpOpen = ref(false)
const mcpForm = ref({ name: '', server_code: '', description: '' })
const mcpCreating = ref(false)
const mcpErr = ref('')

const skillErr = ref('')
const skillFilterName = ref('')
const skillView = ref<'grid' | 'list'>('grid')

const toolFilterName = ref('')
const toolView = ref<'grid' | 'list'>('grid')

const mcpFilterName = ref('')
const mcpView = ref<'grid' | 'list'>('grid')
const mcpDetailOpen = ref(false)
const activeMcp = ref<MCP | null>(null)
const mcpEditForm = ref({
  name: '',
  server_code: '',
  description: '',
  connection_json: '{}',
  capability_json: '{}',
  is_active: true,
})
const mcpSaving = ref(false)
const mcpDeleting = ref(false)

const filteredSkills = computed(() => {
  const q = skillFilterName.value.trim().toLowerCase()
  if (!q) return skills.value
  return skills.value.filter((s) => (s.name || '').toLowerCase().includes(q) || (s.code || '').toLowerCase().includes(q))
})

const filteredTools = computed(() => {
  const q = toolFilterName.value.trim().toLowerCase()
  if (!q) return tools.value
  return tools.value.filter((t) => (t.name || '').toLowerCase().includes(q) || (t.code || '').toLowerCase().includes(q))
})

const filteredMcps = computed(() => {
  const q = mcpFilterName.value.trim().toLowerCase()
  if (!q) return mcps.value
  return mcps.value.filter((m) => (m.name || '').toLowerCase().includes(q) || (m.server_code || '').toLowerCase().includes(q))
})

const createProfileOpen = ref(false)
const creatingProfile = ref(false)
const profileCreateErr = ref('')
const profileForm = ref({ name: '', role: 'assistant', model_name: 'gpt-4.1-mini', soul_md: '' })

async function loadAgents() {
  loadingAgents.value = true
  try {
    const res = await apiListAgents()
    agents.value = res.data
  } finally {
    loadingAgents.value = false
  }
}

async function loadProfiles() {
  loadingProfiles.value = true
  try {
    const res = await apiListAgentProfiles()
    profiles.value = res.data
  } finally {
    loadingProfiles.value = false
  }
}

async function loadTools() {
  loadingTools.value = true
  try {
    const res = await apiListTools()
    tools.value = res.data
  } finally {
    loadingTools.value = false
  }
}

async function loadMcps() {
  loadingMcps.value = true
  try {
    const res = await apiListMcps()
    mcps.value = res.data
  } finally {
    loadingMcps.value = false
  }
}

async function loadSkillPool() {
  loadingSkillPool.value = true
  skillErr.value = ''
  try {
    const res = await apiListAgentSkillPool()
    skills.value = res.data
  } catch (e) {
    skillErr.value = e instanceof Error ? e.message : String(e)
  } finally {
    loadingSkillPool.value = false
  }
}

async function createMcp() {
  mcpErr.value = ''
  const name = mcpForm.value.name.trim()
  const server_code = mcpForm.value.server_code.trim()
  if (!name || !server_code) {
    mcpErr.value = 'name/server_code 必填'
    return
  }
  mcpCreating.value = true
  try {
    await apiCreateMcp({ name, server_code, description: mcpForm.value.description || null })
    createMcpOpen.value = false
    mcpForm.value = { name: '', server_code: '', description: '' }
    await loadMcps()
  } catch (e) {
    mcpErr.value = e instanceof Error ? e.message : String(e)
  } finally {
    mcpCreating.value = false
  }
}

async function createAgent() {
  const name = newAgentName.value.trim()
  if (!name) {
    agentErr.value = '请输入智能体名称'
    return
  }
  agentErr.value = ''
  creatingAgent.value = true
  try {
    await apiCreateAgent({ display_name: name, description: null, template_profile_id: newAgentProfileId.value })
    newAgentName.value = ''
    newAgentProfileId.value = null
    createAgentOpen.value = false
    await loadAgents()
    ElMessage.success('已创建智能体')
  } catch (e) {
    agentErr.value = e instanceof Error ? e.message : String(e)
    ElMessage.error(agentErr.value)
  } finally {
    creatingAgent.value = false
  }
}

async function createProfile() {
  profileCreateErr.value = ''
  const name = profileForm.value.name.trim()
  const role = profileForm.value.role.trim()
  const soul_md = profileForm.value.soul_md.trim()
  if (!name || !role || !soul_md) {
    profileCreateErr.value = 'name/role/soul_md 必填'
    return
  }
  creatingProfile.value = true
  try {
    await apiCreateAgentProfile({ name, role, soul_md, model_name: profileForm.value.model_name })
    createProfileOpen.value = false
    profileForm.value = { name: '', role: 'assistant', model_name: 'gpt-4.1-mini', soul_md: '' }
    await loadProfiles()
  } catch (e) {
    profileCreateErr.value = e instanceof Error ? e.message : String(e)
  } finally {
    creatingProfile.value = false
  }
}

function goAgent(id: string) {
  router.push(`/agents/${id}`)
}

function goProfile(id: string) {
  router.push(`/agent-profiles/${id}`)
}

function openMcp(m: MCP) {
  activeMcp.value = m
  mcpErr.value = ''
  mcpEditForm.value = {
    name: m.name,
    server_code: m.server_code,
    description: m.description || '',
    connection_json: m.connection_json || '{}',
    capability_json: m.capability_json || '{}',
    is_active: !!m.is_active,
  }
  mcpDetailOpen.value = true
}

async function saveMcp() {
  if (!activeMcp.value) return
  mcpErr.value = ''
  const name = mcpEditForm.value.name.trim()
  const server_code = mcpEditForm.value.server_code.trim()
  if (!name || !server_code) {
    mcpErr.value = 'name/server_code 必填'
    return
  }
  mcpSaving.value = true
  try {
    await apiUpdateMcp(activeMcp.value.id, {
      name,
      server_code,
      description: mcpEditForm.value.description || null,
      connection_json: mcpEditForm.value.connection_json || '{}',
      capability_json: mcpEditForm.value.capability_json || '{}',
      is_active: mcpEditForm.value.is_active ? 1 : 0,
    })
    mcpDetailOpen.value = false
    await loadMcps()
  } catch (e) {
    mcpErr.value = e instanceof Error ? e.message : String(e)
  } finally {
    mcpSaving.value = false
  }
}

async function deleteMcp() {
  if (!activeMcp.value) return
  mcpDeleting.value = true
  mcpErr.value = ''
  try {
    await apiDeleteMcp(activeMcp.value.id)
    mcpDetailOpen.value = false
    await loadMcps()
  } catch (e) {
    mcpErr.value = e instanceof Error ? e.message : String(e)
  } finally {
    mcpDeleting.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadAgents(), loadProfiles(), loadTools(), loadMcps(), loadSkillPool()])
})
</script>

<style scoped>
.shell {
  height: calc(100vh - 36px);
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 14px;
}
.centerNav {
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 18px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.title {
  font-weight: 900;
  font-size: 16px;
  margin-bottom: 6px;
}
.navItem {
  height: 44px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  padding: 0 12px;
  cursor: pointer;
  font-weight: 800;
  opacity: 0.85;
}
.navItem:hover {
  background: rgba(79, 140, 255, 0.06);
}
.navItem.active {
  background: rgba(79, 140, 255, 0.12);
  opacity: 1;
}

.content {
  overflow: hidden;
}
.panel {
  height: 100%;
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 18px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.panelHeader {
  height: 64px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(31, 35, 41, 0.06);
}
.panelTitle {
  font-weight: 900;
  font-size: 16px;
}
.actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.list {
  padding: 10px 8px;
  overflow: auto;
  min-height: 0;
}
.row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 12px;
  border-radius: 14px;
  cursor: pointer;
}
.row:hover {
  background: rgba(79, 140, 255, 0.06);
}
.name {
  font-weight: 900;
}
.meta {
  font-size: 12px;
  opacity: 0.65;
  margin-top: 2px;
}
.right {
  font-size: 12px;
  opacity: 0.7;
}
.empty {
  padding: 18px 10px;
  opacity: 0.6;
}
.err {
  color: #d92d20;
  font-size: 12px;
  padding: 0 16px;
  margin-top: 10px;
}
.formGrid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 10px;
}

.skillsToolbar {
  padding: 12px 16px;
  display: grid;
  grid-template-columns: 1fr 180px 80px;
  gap: 10px;
  align-items: center;
  border-bottom: 1px solid rgba(31, 35, 41, 0.06);
}
.viewToggles {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.viewBtn {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: 1px solid rgba(31, 35, 41, 0.1);
  background: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  font-weight: 900;
}
.viewBtn.active {
  background: rgba(31, 35, 41, 0.06);
}

.skillsGrid {
  padding: 14px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  overflow: auto;
  min-height: 0;
}
.skillCard {
  border: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.85);
  padding: 14px;
}
.skillCard.clickable {
  cursor: pointer;
}
.cardTop {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.docIcon {
  width: 40px;
  height: 40px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  background: rgba(79, 140, 255, 0.14);
  font-size: 18px;
}
.status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 800;
  opacity: 0.9;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: rgba(31, 35, 41, 0.25);
}
.dot.on {
  background: #12b76a;
}
.cardName {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 900;
}
.code {
  font-size: 18px;
}
.badge {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(255, 176, 0, 0.16);
  color: #b25a00;
  font-weight: 900;
}
.cardMeta {
  margin-top: 10px;
  display: grid;
  gap: 6px;
  font-size: 12px;
}
.kv {
  display: grid;
  grid-template-columns: 72px 1fr;
  gap: 10px;
}
.k {
  opacity: 0.6;
}
.v {
  opacity: 0.9;
}
.cardDesc {
  margin-top: 10px;
  font-size: 12px;
  opacity: 0.75;
  line-height: 1.5;
}
.templateHint {
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(79, 140, 255, 0.08);
  color: rgba(37, 99, 235, 0.92);
  font-size: 12px;
  line-height: 1.6;
}

.drawerBody {
  padding: 10px 14px;
}
.drawerField {
  margin-bottom: 12px;
}
.label {
  font-weight: 900;
  margin-bottom: 6px;
}
.drawerFooter {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
