import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  apiDeleteAgentFsFile,
  apiGetAgentMcpToggles,
  apiGetAgentSkillConfig,
  apiGetAgentToolToggles,
  apiListAgentFs,
  apiListAgentSkillPool,
  apiListAgents,
  apiListMcps,
  apiListTools,
  apiReadAgentFsFile,
  apiUpdateAgentMcpToggles,
  apiUpdateAgentSkillConfig,
  apiUpdateAgentToolToggles,
  apiWriteAgentFsFile,
  type Agent,
  type FsEntry,
  type MCP,
  type SkillPoolItem,
  type Tool,
} from '../api/agents'

type AgentDetailSection = 'files' | 'skills' | 'knowledge' | 'tools' | 'mcps'
type CoreFileName = 'SOUL.md' | 'PROFILE.md' | 'BOOTSTRAP.md' | 'MEMORY.md'

export function useAgentDetail() {
  const route = useRoute()
  const router = useRouter()

  const agentId = computed(() => String(route.params.id || ''))
  const agent = ref<Agent | null>(null)
  const activeSection = ref<AgentDetailSection>('files')

  const files = ref<FsEntry[]>([])
  const loading = ref(false)
  const content = ref('')
  const originalContent = ref('')
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

  const mcps = ref<MCP[]>([])
  const mcpToggles = ref<Record<string, boolean>>({})
  const mcpSaving = ref(false)

  const activeCoreFile = ref<CoreFileName>('SOUL.md')
  const activeKnowledgePath = ref('')
  const knowledgeDialogOpen = ref(false)

  const coreFileOptions: Array<{
    label: string
    value: CoreFileName
  }> = [
    { label: 'SOUL.md', value: 'SOUL.md' },
    { label: 'PROFILE.md', value: 'PROFILE.md' },
    { label: 'BOOTSTRAP.md', value: 'BOOTSTRAP.md' },
    { label: 'MEMORY.md', value: 'MEMORY.md' },
  ]

  const coreFiles = computed(() =>
    coreFileOptions.map((item) => ({
      ...item,
      path: item.value,
    })),
  )

  const knowledgeFiles = computed(() =>
    files.value
      .filter((entry) => !entry.is_dir && entry.path.startsWith('knowledge/'))
      .map((entry) => ({ path: entry.path, label: entry.path.replace(/^knowledge\//, '') })),
  )

  const activeFilePath = computed(() => activeCoreFile.value)
  const canDeleteCoreFile = computed(() => activeCoreFile.value !== 'SOUL.md' && activeCoreFile.value !== 'PROFILE.md')
  const canSaveActiveFile = computed(
    () => activeSection.value === 'files' || (activeSection.value === 'knowledge' && !!activeKnowledgePath.value),
  )

  async function loadAgentMeta() {
    const res = await apiListAgents()
    agent.value = res.data.find((a) => String(a.id) === agentId.value) || null
  }

  async function loadFiles() {
    const res = await apiListAgentFs(agentId.value)
    files.value = res.data || []
  }

  async function loadTools() {
    const res = await apiListTools()
    tools.value = res.data || []
  }

  async function loadToolToggles() {
    const res = await apiGetAgentToolToggles(agentId.value)
    toolToggles.value = res.data.enabled || {}
  }

  async function loadSkillPool() {
    const res = await apiListAgentSkillPool()
    skillPool.value = res.data || []
  }

  async function loadSkillConfig() {
    const res = await apiGetAgentSkillConfig(agentId.value)
    skillConfig.value = {
      enable_agent_local_skills: !!res.data.enable_agent_local_skills,
      pool_skill_codes: Array.isArray(res.data.pool_skill_codes) ? [...res.data.pool_skill_codes] : [],
    }
  }

  async function loadMcps() {
    const res = await apiListMcps()
    mcps.value = res.data || []
  }

  async function loadMcpToggles() {
    const res = await apiGetAgentMcpToggles(agentId.value)
    mcpToggles.value = res.data.enabled || {}
  }

  function toggleSkillPoolCode(code: string, checked: boolean) {
    const next = new Set(skillConfig.value.pool_skill_codes)
    if (checked) next.add(code)
    else next.delete(code)
    skillConfig.value.pool_skill_codes = Array.from(next)
  }

  function toggleTool(code: string, checked: boolean) {
    toolToggles.value = { ...toolToggles.value, [code]: checked }
  }

  function toggleMcp(code: string, checked: boolean) {
    mcpToggles.value = { ...mcpToggles.value, [code]: checked }
  }

  async function loadActiveCoreFile() {
    err.value = ''
    try {
      const res = await apiReadAgentFsFile(agentId.value, activeCoreFile.value)
      content.value = res.data.content || ''
      originalContent.value = content.value
    } catch (e) {
      err.value = e instanceof Error ? e.message : String(e)
    }
  }

  async function reloadAll() {
    err.value = ''
    if (!agentId.value) return
    loading.value = true
    try {
      await Promise.all([
        loadAgentMeta(),
        loadFiles(),
        loadTools(),
        loadToolToggles(),
        loadSkillPool(),
        loadSkillConfig(),
        loadMcps(),
        loadMcpToggles(),
      ])
      await loadActiveCoreFile()
    } catch (e) {
      err.value = e instanceof Error ? e.message : String(e)
    } finally {
      loading.value = false
    }
  }

  async function saveActiveFile() {
    if (activeSection.value === 'files') {
      if (!canDeleteCoreFile.value && activeCoreFile.value === 'SOUL.md') {
        err.value = 'SOUL.md 不能删除，仍可编辑'
      }
      saving.value = true
      try {
        await apiWriteAgentFsFile(agentId.value, activeCoreFile.value, content.value)
        originalContent.value = content.value
        ElMessage.success('已保存文件')
      } catch (e) {
        err.value = e instanceof Error ? e.message : String(e)
        ElMessage.error(err.value)
      } finally {
        saving.value = false
      }
      return
    }

    if (activeSection.value === 'knowledge' && activeKnowledgePath.value) {
      saving.value = true
      try {
        await apiWriteAgentFsFile(agentId.value, activeKnowledgePath.value, content.value)
        originalContent.value = content.value
        ElMessage.success('已保存文件')
      } catch (e) {
        err.value = e instanceof Error ? e.message : String(e)
        ElMessage.error(err.value)
      } finally {
        saving.value = false
      }
    }
  }

  function resetContent() {
    content.value = originalContent.value
  }

  async function copyContent() {
    try {
      await navigator.clipboard.writeText(content.value)
      ElMessage.success('已复制到剪贴板')
    } catch (e) {
      ElMessage.error(e instanceof Error ? e.message : String(e))
    }
  }

  async function deleteCoreFile() {
    if (!canDeleteCoreFile.value) return
    try {
      await apiDeleteAgentFsFile(agentId.value, activeCoreFile.value)
      activeCoreFile.value = 'PROFILE.md'
      await loadActiveCoreFile()
      await loadFiles()
    } catch (e) {
      err.value = e instanceof Error ? e.message : String(e)
    }
  }

  async function openKnowledge(path: string) {
    activeSection.value = 'knowledge'
    activeKnowledgePath.value = path
    knowledgeDialogOpen.value = true
    try {
      const res = await apiReadAgentFsFile(agentId.value, path)
      content.value = res.data.content || ''
      originalContent.value = content.value
    } catch (e) {
      err.value = e instanceof Error ? e.message : String(e)
    }
  }

  async function saveSkillConfig() {
    skillSaving.value = true
    try {
      await apiUpdateAgentSkillConfig(agentId.value, {
        enable_agent_local_skills: !!skillConfig.value.enable_agent_local_skills,
        pool_skill_codes: Array.from(new Set(skillConfig.value.pool_skill_codes)),
      })
      ElMessage.success('已保存技能配置')
    } catch (e) {
      ElMessage.error(e instanceof Error ? e.message : String(e))
    } finally {
      skillSaving.value = false
    }
  }

  async function saveToolToggles() {
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

  async function saveMcpToggles() {
    mcpSaving.value = true
    try {
      await apiUpdateAgentMcpToggles(agentId.value, mcpToggles.value)
      ElMessage.success('已保存 MCP 开关')
    } catch (e) {
      ElMessage.error(e instanceof Error ? e.message : String(e))
    } finally {
      mcpSaving.value = false
    }
  }

  function openKnowledgeDialog(path: string) {
    void openKnowledge(path)
  }

  watch(activeCoreFile, async () => {
    if (activeSection.value !== 'files') return
    await loadActiveCoreFile()
  })

  watch(activeSection, async (next) => {
    if (next === 'files') {
      await loadActiveCoreFile()
    }
  })

  onMounted(async () => {
    await reloadAll()
  })

  return {
    agentId,
    agent,
    activeSection,
    files,
    loading,
    content,
    originalContent,
    saving,
    err,
    tools,
    toolToggles,
    toolSaving,
    skillPool,
    skillConfig,
    skillSaving,
    mcps,
    mcpToggles,
    mcpSaving,
    activeCoreFile,
    activeKnowledgePath,
    knowledgeDialogOpen,
    coreFiles,
    knowledgeFiles,
    activeFilePath,
    canDeleteCoreFile,
    canSaveActiveFile,
    reloadAll,
    saveActiveFile,
    resetContent,
    copyContent,
    deleteCoreFile,
    openKnowledge: openKnowledgeDialog,
    saveSkillConfig,
    saveToolToggles,
    saveMcpToggles,
    toggleSkillPoolCode,
    toggleTool,
    toggleMcp,
    loadActiveCoreFile,
    router,
  }
}
