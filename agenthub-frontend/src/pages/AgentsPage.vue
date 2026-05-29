<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import AppRail from '@/components/chat/AppRail.vue'
import {
  getMe,
  listAcpProviders,
  listMcps,
  listSkills,
  type AcpProviderResource,
  type McpResource,
  type SkillResource,
} from '@/services/agenthubService'
import AgentManagePage from './AgentManagePage.vue'
import AgentTemplatePage from './AgentTemplatePage.vue'

const router = useRouter()
const loading = ref(false)
type AgentPageSection = 'agents' | 'templates' | 'acp' | 'skills' | 'mcps'
const activePageSection = ref<AgentPageSection>('agents')

const mcps = ref<McpResource[]>([])
const skills = ref<SkillResource[]>([])
const acpProviders = ref<AcpProviderResource[]>([])

const pageSections = [
  { key: 'agents', label: '智能体管理' },
  { key: 'templates', label: '智能体模板' },
  { key: 'acp', label: 'ACP 配置' },
  { key: 'skills', label: '技能池' },
  { key: 'mcps', label: 'MCP 配置' },
] satisfies Array<{ key: AgentPageSection; label: string }>

async function logout() {
  localStorage.removeItem('token')
  await router.replace({ name: 'login' })
}

async function loadAll() {
  const [mcpRows, skillRows, acpRows] = await Promise.all([
    listMcps(),
    listSkills(),
    listAcpProviders(),
  ])
  mcps.value = mcpRows
  skills.value = skillRows
  acpProviders.value = acpRows
}

async function bootstrap() {
  loading.value = true
  try {
    await getMe()
    await loadAll()
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
        <div class="brand-subtitle">智能体控制台</div>
      </div>

      <button
        v-for="section in pageSections"
        :key="section.key"
        class="nav-item"
        :class="{ active: activePageSection === section.key }"
        @click="activePageSection = section.key"
      >
        {{ section.label }}
      </button>
    </aside>

    <main class="agent-main">
      <template v-if="activePageSection === 'agents'">
        <AgentManagePage />
      </template>

      <template v-else-if="activePageSection === 'templates'">
        <AgentTemplatePage />
      </template>

      <template v-else-if="activePageSection === 'acp'">
        <div class="resource-page">
          <div class="resource-page-head">
            <div>
              <div class="page-title">ACP 配置</div>
              <div class="page-subtitle">统一管理外部执行器和接入 Provider。</div>
            </div>
          </div>
          <div class="resource-grid">
            <div v-for="item in acpProviders" :key="item.id" class="resource-card large">
              <div class="resource-name">{{ item.name }}</div>
              <div class="resource-meta">Provider：{{ item.provider_type }}</div>
              <div class="resource-meta">Transport：{{ item.transport_type }}</div>
              <div class="resource-meta">Endpoint：{{ item.endpoint || '未配置' }}</div>
            </div>
          </div>
        </div>
      </template>

      <template v-else-if="activePageSection === 'skills'">
        <div class="resource-page">
          <div class="resource-page-head">
            <div>
              <div class="page-title">技能池</div>
              <div class="page-subtitle">维护可供智能体复用的技能能力。</div>
            </div>
          </div>
          <div class="resource-grid">
            <div v-for="item in skills" :key="item.id" class="resource-card large">
              <div class="resource-name">{{ item.name }}</div>
              <div class="resource-meta">Code：{{ item.code }}</div>
              <div class="resource-meta">Version：{{ item.version }}</div>
              <div class="resource-meta">{{ item.description || '暂无描述' }}</div>
            </div>
          </div>
        </div>
      </template>

      <template v-else>
        <div class="resource-page">
          <div class="resource-page-head">
            <div>
              <div class="page-title">MCP 配置</div>
              <div class="page-subtitle">统一管理可挂载的 MCP Server 能力。</div>
            </div>
          </div>
          <div class="resource-grid">
            <div v-for="item in mcps" :key="item.id" class="resource-card large">
              <div class="resource-name">{{ item.name }}</div>
              <div class="resource-meta">Server Code：{{ item.server_code }}</div>
              <div class="resource-meta">{{ item.description || '暂无描述' }}</div>
            </div>
          </div>
        </div>
      </template>
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

.nav-item {
  width: 100%;
  margin-bottom: 10px;
  padding: 16px 18px;
  border-radius: 18px;
  border: 0;
  background: transparent;
  font-size: 18px;
  text-align: left;
  color: #1f2329;
}

.nav-item.active,
.nav-item:hover {
  background: rgba(255, 255, 255, 0.72);
}

.agent-main {
  padding: 24px 28px;
  overflow: auto;
}

.resource-page {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 24px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
}

.page-title,
.page-title {
  font-size: 18px;
  font-weight: 700;
  color: #1f2329;
}
.page-subtitle,
.page-subtitle,
.content-breadcrumb {
  color: rgba(31, 35, 41, 0.5);
  font-size: 13px;
}

.resource-grid,
.resource-card {
  padding: 20px;
  border-radius: 22px;
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.06);
}

.resource-card.large {
  min-height: 160px;
}

.resource-name {
  font-size: 28px;
  font-weight: 700;
  color: #1f2329;
}

.resource-meta {
  margin-top: 10px;
  color: rgba(31, 35, 41, 0.56);
  line-height: 1.7;
}

.resource-page {
  padding: 26px;
}

.resource-page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 18px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
}

.empty-wrap {
  display: grid;
  place-items: center;
  min-height: 220px;
}
</style>
