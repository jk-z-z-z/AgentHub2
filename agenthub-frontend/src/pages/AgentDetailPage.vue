<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import AppRail from '@/components/chat/AppRail.vue'
import {
  bindProfileAcpProviders,
  bindProfileMcps,
  bindProfileSkills,
  bindProfileTools,
  getMe,
  listAcpProviders,
  listAgentInstances,
  listAgentProfiles,
  listGroups,
  listMcps,
  listSkills,
  listTools,
  type AcpProviderResource,
  type AgentInstance,
  type AgentProfile,
  type Group,
  type McpResource,
  type SkillResource,
  type ToolResource,
} from '@/services/agenthubService'

type AgentConfigSection = 'files' | 'skills' | 'tools' | 'mcps' | 'acp' | 'runtime' | 'stats'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const activeConfigSection = ref<AgentConfigSection>('skills')

const groups = ref<Group[]>([])
const profiles = ref<AgentProfile[]>([])
const instances = ref<AgentInstance[]>([])
const tools = ref<ToolResource[]>([])
const mcps = ref<McpResource[]>([])
const skills = ref<SkillResource[]>([])
const acpProviders = ref<AcpProviderResource[]>([])

const profileToolIds = ref<string[]>([])
const profileMcpIds = ref<string[]>([])
const profileSkillIds = ref<string[]>([])
const profileAcpIds = ref<string[]>([])

const configSections = [
  { key: 'files', label: '文件' },
  { key: 'skills', label: '技能' },
  { key: 'tools', label: '工具' },
  { key: 'mcps', label: 'MCP' },
  { key: 'acp', label: 'ACP' },
  { key: 'runtime', label: '运行配置' },
  { key: 'stats', label: '智能体统计' },
] satisfies Array<{ key: AgentConfigSection; label: string }>

const selectedInstanceId = computed(() => String(route.params.id || ''))
const selectedInstance = computed(() => instances.value.find((item) => item.id === selectedInstanceId.value) ?? null)
const selectedProfile = computed(() =>
  profiles.value.find((item) => item.id === selectedInstance.value?.profile_id) ?? null,
)

const currentGroupName = computed(() => {
  const group = groups.value.find((item) => item.id === selectedInstance.value?.group_id)
  return group?.name || selectedInstance.value?.group_id || '未分配'
})

const resourceSummary = computed(() => ({
  tools: profileToolIds.value.length,
  mcps: profileMcpIds.value.length,
  skills: profileSkillIds.value.length,
  acp: profileAcpIds.value.length,
}))

async function logout() {
  localStorage.removeItem('token')
  await router.replace({ name: 'login' })
}

async function bootstrap() {
  loading.value = true
  try {
    await getMe()
    const [groupRows, profileRows, instanceRows, toolRows, mcpRows, skillRows, acpRows] = await Promise.all([
      listGroups(),
      listAgentProfiles(),
      listAgentInstances(),
      listTools(),
      listMcps(),
      listSkills(),
      listAcpProviders(),
    ])
    groups.value = groupRows
    profiles.value = profileRows
    instances.value = instanceRows
    tools.value = toolRows
    mcps.value = mcpRows
    skills.value = skillRows
    acpProviders.value = acpRows

    if (!instanceRows.some((item) => item.id === selectedInstanceId.value)) {
      ElMessage.warning('该智能体不存在，已返回列表')
      await router.replace({ name: 'agents' })
    }
  } catch (error) {
    const text = error instanceof Error ? error.message : String(error)
    if (text.includes('401')) {
      await logout()
      return
    }
    ElMessage.error(text)
  } finally {
    loading.value = false
  }
}

async function syncBindings() {
  if (!selectedProfile.value) {
    ElMessage.warning('当前智能体没有关联模板')
    return
  }
  loading.value = true
  try {
    await Promise.all([
      bindProfileTools(selectedProfile.value.id, profileToolIds.value),
      bindProfileMcps(selectedProfile.value.id, profileMcpIds.value),
      bindProfileSkills(selectedProfile.value.id, profileSkillIds.value),
      bindProfileAcpProviders(selectedProfile.value.id, profileAcpIds.value),
    ])
    ElMessage.success('资源绑定已保存')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : String(error))
  } finally {
    loading.value = false
  }
}

watch(
  selectedProfile,
  (profile) => {
    if (!profile) {
      profileToolIds.value = []
      profileMcpIds.value = []
      profileSkillIds.value = []
      profileAcpIds.value = []
    }
  },
  { immediate: true },
)

onMounted(() => {
  void bootstrap()
})
</script>

<template>
  <div v-loading="loading" class="agent-shell">
    <AppRail @logout="logout" />

    <aside class="agent-nav">
      <div class="brand-block">
        <div class="brand-title">AgentHub</div>
        <div class="brand-subtitle">智能体详情</div>
      </div>

      <button class="back-button" @click="router.push({ name: 'agents' })">← 返回智能体管理</button>

      <button
        v-for="section in configSections"
        :key="section.key"
        class="config-nav-item"
        :class="{ active: activeConfigSection === section.key }"
        @click="activeConfigSection = section.key"
      >
        {{ section.label }}
      </button>
    </aside>

    <main class="agent-main">
      <div class="config-content-card">
        <div class="content-head">
          <div>
            <div class="content-breadcrumb">智能体管理 / {{ selectedInstance?.display_name || '详情' }}</div>
            <div class="content-title">{{ configSections.find((item) => item.key === activeConfigSection)?.label }}</div>
          </div>
          <el-button type="success" :disabled="!selectedProfile" @click="syncBindings">保存配置</el-button>
        </div>

        <template v-if="activeConfigSection === 'files'">
          <div class="info-card">
            <div class="card-title">工作区文件</div>
            <div class="card-desc">当前阶段先展示文件能力入口，后续可接 Workspace、仓库和沙箱目录配置。</div>
            <div class="kv-list">
              <div class="kv-row"><span>当前智能体</span><span>{{ selectedInstance?.display_name || '未选择' }}</span></div>
              <div class="kv-row"><span>所属群组</span><span>{{ currentGroupName }}</span></div>
              <div class="kv-row"><span>运行状态</span><span>{{ selectedInstance?.status || '未配置' }}</span></div>
            </div>
          </div>
        </template>

        <template v-else-if="activeConfigSection === 'skills'">
          <div class="bind-card">
            <div class="card-title">技能绑定</div>
            <el-select v-model="profileSkillIds" multiple collapse-tags collapse-tags-tooltip placeholder="选择技能">
              <el-option v-for="item in skills" :key="item.id" :label="item.name" :value="item.id" />
            </el-select>
          </div>
          <div class="resource-grid">
            <div v-for="item in skills" :key="item.id" class="resource-card">
              <div class="resource-name">{{ item.name }}</div>
              <div class="resource-meta">版本：{{ item.version }}</div>
              <div class="resource-meta">{{ item.description || '暂无描述' }}</div>
            </div>
          </div>
        </template>

        <template v-else-if="activeConfigSection === 'tools'">
          <div class="bind-card">
            <div class="card-title">工具绑定</div>
            <el-select v-model="profileToolIds" multiple collapse-tags collapse-tags-tooltip placeholder="选择工具">
              <el-option v-for="item in tools" :key="item.id" :label="item.name" :value="item.id" />
            </el-select>
          </div>
          <div class="resource-grid">
            <div v-for="item in tools" :key="item.id" class="resource-card">
              <div class="resource-name">{{ item.name }}</div>
              <div class="resource-meta">类型：{{ item.source_type }}</div>
              <div class="resource-meta">{{ item.description || '暂无描述' }}</div>
            </div>
          </div>
        </template>

        <template v-else-if="activeConfigSection === 'mcps'">
          <div class="bind-card">
            <div class="card-title">MCP 绑定</div>
            <el-select v-model="profileMcpIds" multiple collapse-tags collapse-tags-tooltip placeholder="选择 MCP">
              <el-option v-for="item in mcps" :key="item.id" :label="item.name" :value="item.id" />
            </el-select>
          </div>
          <div class="resource-grid">
            <div v-for="item in mcps" :key="item.id" class="resource-card">
              <div class="resource-name">{{ item.name }}</div>
              <div class="resource-meta">编码：{{ item.server_code }}</div>
              <div class="resource-meta">{{ item.description || '暂无描述' }}</div>
            </div>
          </div>
        </template>

        <template v-else-if="activeConfigSection === 'acp'">
          <div class="bind-card">
            <div class="card-title">ACP 绑定</div>
            <el-select v-model="profileAcpIds" multiple collapse-tags collapse-tags-tooltip placeholder="选择 ACP Provider">
              <el-option v-for="item in acpProviders" :key="item.id" :label="item.name" :value="item.id" />
            </el-select>
          </div>
          <div class="resource-grid">
            <div v-for="item in acpProviders" :key="item.id" class="resource-card">
              <div class="resource-name">{{ item.name }}</div>
              <div class="resource-meta">类型：{{ item.provider_type }}</div>
              <div class="resource-meta">{{ item.endpoint || '未配置 Endpoint' }}</div>
            </div>
          </div>
        </template>

        <template v-else-if="activeConfigSection === 'runtime'">
          <div class="info-card">
            <div class="card-title">运行配置</div>
            <div class="kv-list">
              <div class="kv-row"><span>Base URL</span><span>{{ selectedInstance?.base_url || '未配置' }}</span></div>
              <div class="kv-row"><span>API Key Ref</span><span>{{ selectedInstance?.api_key_ref || '未配置' }}</span></div>
              <div class="kv-row"><span>Config JSON</span><span>{{ selectedInstance?.config_json || '{}' }}</span></div>
              <div class="kv-row"><span>Planning Mode</span><span>{{ selectedProfile?.planning_mode || '未配置' }}</span></div>
            </div>
          </div>
        </template>

        <template v-else>
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-label">技能数</div>
              <div class="stat-value">{{ resourceSummary.skills }}</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">工具数</div>
              <div class="stat-value">{{ resourceSummary.tools }}</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">MCP 数</div>
              <div class="stat-value">{{ resourceSummary.mcps }}</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">ACP 数</div>
              <div class="stat-value">{{ resourceSummary.acp }}</div>
            </div>
          </div>
        </template>
      </div>
    </main>
  </div>
</template>

<style scoped>
.agent-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 84px 280px 1fr;
  background: #f6f4ef;
}

.agent-nav {
  padding: 28px 18px;
  background: #f1ede6;
  border-right: 1px solid rgba(15, 23, 42, 0.06);
}

.brand-block {
  padding: 8px 8px 20px;
}

.brand-title {
  font-size: 28px;
  font-weight: 700;
  color: #1f2329;
}

.brand-subtitle {
  margin-top: 6px;
  color: rgba(31, 35, 41, 0.48);
}

.back-button,
.config-nav-item {
  width: 100%;
  border: 0;
  text-align: left;
  border-radius: 18px;
  background: transparent;
  color: #1f2329;
}

.back-button {
  margin-bottom: 18px;
  padding: 16px 18px;
  font-size: 16px;
  background: rgba(255, 255, 255, 0.7);
}

.config-nav-item {
  margin-bottom: 10px;
  padding: 16px 18px;
  font-size: 18px;
}

.config-nav-item.active,
.config-nav-item:hover {
  background: rgba(255, 255, 255, 0.72);
}

.agent-main {
  padding: 24px 28px;
  overflow: auto;
}

.config-content-card {
  min-height: calc(100vh - 48px);
  padding: 24px 28px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 24px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
}

.content-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
}

.content-breadcrumb {
  color: rgba(31, 35, 41, 0.5);
  font-size: 13px;
}

.content-title {
  margin-top: 8px;
  font-size: 34px;
  font-weight: 700;
  color: #1f2329;
}

.bind-card,
.info-card {
  margin-top: 24px;
  padding: 22px;
  border-radius: 20px;
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.06);
}

.card-title {
  margin-bottom: 16px;
  font-size: 18px;
  font-weight: 700;
  color: #1f2329;
}

.card-desc {
  color: rgba(31, 35, 41, 0.6);
  line-height: 1.7;
}

.kv-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.kv-row {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 16px;
  color: #1f2329;
}

.resource-grid,
.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-top: 20px;
}

.resource-card,
.stat-card {
  padding: 20px;
  border-radius: 22px;
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.06);
}

.resource-name,
.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #1f2329;
}

.resource-meta,
.stat-label {
  margin-top: 10px;
  color: rgba(31, 35, 41, 0.56);
  line-height: 1.7;
}
</style>
