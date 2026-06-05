<template>
  <div class="shell">
    <aside class="centerNav">
      <div class="title">智能体中心</div>
      <el-menu class="navMenu" :default-active="section" @select="section = $event">
        <el-menu-item index="instances">智能体管理</el-menu-item>
        <el-menu-item index="templates">模版管理</el-menu-item>
        <el-menu-item index="tools">工具（全局）</el-menu-item>
        <el-menu-item index="mcps">MCP（全局）</el-menu-item>
        <el-menu-item index="skills">技能（全局）</el-menu-item>
      </el-menu>
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
        <el-table
          :data="agents"
          class="table"
          height="100%"
          empty-text="暂无智能体"
          @row-click="handleAgentRowClick"
        >
          <el-table-column label="智能体" min-width="220">
            <template #default="{ row }">
              <div class="name">{{ row.display_name }}</div>
              <div class="meta">#{{ row.id }}</div>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="120" />
          <el-table-column label="操作" width="90" align="right">
            <template #default>
              <span class="right">编辑 ›</span>
            </template>
          </el-table-column>
        </el-table>
      </section>

      <section v-else-if="section === 'templates'" class="panel">
        <div class="panelHeader">
          <div class="panelTitle">模版管理</div>
          <div class="actions">
            <el-button @click="loadProfiles" :loading="loadingProfiles">刷新</el-button>
            <el-button type="primary" @click="createProfileOpen = true">新建模版</el-button>
          </div>
        </div>
        <el-table
          :data="profiles"
          class="table"
          height="100%"
          empty-text="暂无模版"
          @row-click="handleProfileRowClick"
        >
          <el-table-column label="模版" min-width="220">
            <template #default="{ row }">
              <div class="name">{{ row.name }}</div>
              <div class="meta">{{ row.role }} · {{ row.model_name }}</div>
            </template>
          </el-table-column>
          <el-table-column prop="role" label="角色" width="120" />
          <el-table-column label="操作" width="120" align="right">
            <template #default>
              <span class="right">在详情页编辑</span>
            </template>
          </el-table-column>
        </el-table>
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
            <el-button class="viewBtn" :class="{ active: toolView === 'grid' }" text :icon="Grid" @click="toolView = 'grid'" />
            <el-button class="viewBtn" :class="{ active: toolView === 'list' }" text :icon="List" @click="toolView = 'list'" />
          </div>
        </div>

        <div v-if="toolView === 'grid'" class="skillsGrid">
          <el-card v-for="t in filteredTools" :key="t.id" class="skillCard" shadow="never">
            <div class="cardTop">
              <div class="docIcon">
                <el-icon>
                  <Tools />
                </el-icon>
              </div>
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
          </el-card>
          <el-empty v-if="!loadingTools && filteredTools.length === 0" description="暂无工具" />
        </div>

        <el-table v-else :data="filteredTools" class="table" height="100%" empty-text="暂无工具">
          <el-table-column label="工具" min-width="220">
            <template #default="{ row }">
              <div class="name">{{ row.name }}</div>
              <div class="meta">{{ row.code }}</div>
            </template>
          </el-table-column>
          <el-table-column prop="source_type" label="来源" width="140" />
          <el-table-column label="说明" min-width="240">
            <template #default>
              内置
            </template>
          </el-table-column>
        </el-table>
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
            <el-button class="viewBtn" :class="{ active: mcpView === 'grid' }" text :icon="Grid" @click="mcpView = 'grid'" />
            <el-button class="viewBtn" :class="{ active: mcpView === 'list' }" text :icon="List" @click="mcpView = 'list'" />
          </div>
        </div>

        <div v-if="mcpView === 'grid'" class="skillsGrid">
          <el-card v-for="m in filteredMcps" :key="m.id" class="skillCard clickable" shadow="never" @click="openMcp(m)">
            <div class="cardTop">
              <div class="docIcon">
                <el-icon>
                  <Connection />
                </el-icon>
              </div>
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
          </el-card>
          <el-empty v-if="!loadingMcps && filteredMcps.length === 0" description="暂无 MCP" />
        </div>

        <el-table
          v-else
          :data="filteredMcps"
          class="table"
          height="100%"
          empty-text="暂无 MCP"
          @row-click="openMcp"
        >
          <el-table-column label="MCP" min-width="220">
            <template #default="{ row }">
              <div class="name">{{ row.name }}</div>
              <div class="meta">{{ row.server_code }}</div>
            </template>
          </el-table-column>
          <el-table-column prop="is_active" label="启用" width="120">
            <template #default="{ row }">
              {{ row.is_active ? '已启用' : '未启用' }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="90" align="right">
            <template #default>
              <span class="right">编辑</span>
            </template>
          </el-table-column>
        </el-table>
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
            <el-button class="viewBtn" :class="{ active: skillView === 'grid' }" text :icon="Grid" @click="skillView = 'grid'" />
            <el-button class="viewBtn" :class="{ active: skillView === 'list' }" text :icon="List" @click="skillView = 'list'" />
          </div>
        </div>

        <div v-if="skillErr" class="err">{{ skillErr }}</div>
        <div v-if="skillView === 'grid'" class="skillsGrid">
          <el-card v-for="s in filteredSkills" :key="s.code" class="skillCard" shadow="never">
            <div class="cardTop">
              <div class="docIcon">
                <el-icon>
                  <Document />
                </el-icon>
              </div>
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
          </el-card>
          <el-empty v-if="!loadingSkillPool && filteredSkills.length === 0" description="暂无技能" />
        </div>

        <el-table v-else :data="filteredSkills" class="table" height="100%" empty-text="暂无技能">
          <el-table-column label="技能" min-width="220">
            <template #default="{ row }">
              <div class="name">{{ row.code }}</div>
              <div class="meta">{{ row.name }}</div>
            </template>
          </el-table-column>
          <el-table-column prop="dir" label="目录" min-width="240" />
          <el-table-column label="说明" width="100" align="right">
            <template #default>
              <span class="right">目录技能</span>
            </template>
          </el-table-column>
        </el-table>
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

  <el-dialog v-model="createProfileOpen" title="新建智能体模版" width="860px">
    <div class="formGrid">
      <el-input v-model="profileForm.name" placeholder="name" />
      <el-input v-model="profileForm.role" placeholder="role" />
      <el-input v-model="profileForm.model_name" placeholder="model_name" />
    </div>
    <el-tabs style="margin-top: 10px" type="border-card">
      <el-tab-pane label="SOUL.md">
        <el-input v-model="profileForm.soul_md" type="textarea" :rows="12" placeholder="模版 SOUL.md（最高优先级规则/边界）" />
      </el-tab-pane>
      <el-tab-pane label="PROFILE.md">
        <el-input v-model="profileForm.profile_md" type="textarea" :rows="12" placeholder="模版 PROFILE.md（角色说明/协作约定/输出规范等）" />
      </el-tab-pane>
      <el-tab-pane label="BOOTSTRAP.md">
        <el-input v-model="profileForm.bootstrap_md" type="textarea" :rows="12" placeholder="模版 BOOTSTRAP.md（创建实例时的引导提问规范）" />
      </el-tab-pane>
      <el-tab-pane label="tools.json">
        <el-input v-model="profileForm.tools_json" type="textarea" :rows="12" placeholder='{"enabled": {"builtin.xxx": true}}' />
      </el-tab-pane>
      <el-tab-pane label="skills.json">
        <el-input v-model="profileForm.skills_json" type="textarea" :rows="12" placeholder='{"enable_agent_local_skills": true, "pool_skill_codes": []}' />
      </el-tab-pane>
    </el-tabs>
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
import { Connection, Document, Grid, List, Tools } from '@element-plus/icons-vue'
import {
  apiCreateAgent,
  apiCreateAgentProfile,
  apiCreateMcp,
  apiDeleteMcp,
  apiGetAgentBootstrapGroup,
  apiStartAgentBootstrap,
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
} from '../api/agents'

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
const defaultProfileForm = () => ({
  name: '',
  role: 'assistant',
  model_name: 'gpt-4.1-mini',
  soul_md: '',
  profile_md: '',
  bootstrap_md: '',
  tools_json: JSON.stringify({ enabled: {} }, null, 2),
  skills_json: JSON.stringify({ enable_agent_local_skills: true, pool_skill_codes: [] }, null, 2),
})
const profileForm = ref(defaultProfileForm())

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
    const res = await apiCreateAgent({ display_name: name, description: null, template_profile_id: newAgentProfileId.value })
    newAgentName.value = ''
    newAgentProfileId.value = null
    createAgentOpen.value = false
    await loadAgents()
    ElMessage.success('已创建智能体')
    if (res?.data?.id) {
      try {
        const boot = await apiGetAgentBootstrapGroup(String(res.data.id))
        if (boot?.data?.id) {
          try {
            await apiStartAgentBootstrap(String(res.data.id))
          } catch {
            // ignore
          }
          router.push({ name: 'messages', query: { groupId: String(boot.data.id) } })
        }
      } catch {
        // ignore
      }
    }
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
    const res = await apiCreateAgentProfile({
      name,
      role,
      soul_md,
      model_name: profileForm.value.model_name,
      profile_md: profileForm.value.profile_md || '',
      bootstrap_md: profileForm.value.bootstrap_md || '',
      tools_json: profileForm.value.tools_json || '',
      skills_json: profileForm.value.skills_json || '',
    })
    createProfileOpen.value = false
    profileForm.value = defaultProfileForm()
    await loadProfiles()
    if (res?.data?.id) router.push(`/agent-profiles/${res.data.id}`)
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

function handleAgentRowClick(row: Agent) {
  goAgent(String(row.id))
}

function handleProfileRowClick(row: AgentProfile) {
  goProfile(String(row.id))
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
  height: 100%;
  display: grid;
  grid-template-columns: 340px minmax(0, 1fr);
  gap: 12px;
}
.centerNav {
  background: rgba(255, 255, 255, 0.84);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 18px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow: auto;
}
.title {
  font-weight: 900;
  font-size: 18px;
  margin-bottom: 6px;
}
.navMenu {
  border-right: 0;
  background: transparent;
}
.navMenu :deep(.el-menu-item) {
  border-radius: 12px;
  margin-bottom: 6px;
  font-weight: 700;
}
.navMenu :deep(.el-menu-item.is-active) {
  background: rgba(79, 140, 255, 0.12);
}

.content {
  overflow: hidden;
  min-width: 0;
}
.panel {
  height: 100%;
  background: rgba(255, 255, 255, 0.84);
  backdrop-filter: blur(10px);
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
  padding: 12px 14px;
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
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
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
  border: 1px solid rgba(31, 35, 41, 0.07);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.85);
  padding: 0;
  overflow: hidden;
}
.skillCard :deep(.el-card__body) {
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
