<template>
  <div class="shell">
    <WorkspacePanel :title="`智能体详情：${agent?.display_name || agentId}`">
      <template #actions>
        <el-button @click="router.push('/agents')">返回管理</el-button>
        <el-button @click="reloadAll" :disabled="!agentId || loading">刷新</el-button>
        <el-button type="primary" @click="saveActiveFile" :loading="saving" :disabled="!canSaveActiveFile">
          保存文件
        </el-button>
      </template>

      <el-tabs v-model="activeSection" class="detailTabs">
        <el-tab-pane label="文件" name="files">
          <AgentDetailFilesPanel
            :files="coreFiles"
            :active-file="activeCoreFile"
            :active-path="activeFilePath"
            :content="content"
            :dirty="content !== originalContent"
            :saving="saving"
            :can-delete="canDeleteCoreFile"
            :err="err"
            @select-file="activeCoreFile = $event"
            @update:content="content = $event"
            @save="saveActiveFile"
            @reset="resetContent"
            @copy="copyContent"
            @delete-file="deleteCoreFile"
          />
        </el-tab-pane>

        <el-tab-pane label="技能" name="skills">
          <AgentDetailSkillsPanel
            :skills="skillPool"
            :selected-codes="skillConfig.pool_skill_codes"
            :enable-local-skills="skillConfig.enable_agent_local_skills"
            :saving="skillSaving"
            @toggle-skill="toggleSkillPoolCode"
            @update:enable-local-skills="skillConfig.enable_agent_local_skills = $event"
            @save="saveSkillConfig"
          />
        </el-tab-pane>

        <el-tab-pane label="知识库" name="knowledge">
          <AgentDetailKnowledgePanel :files="knowledgeFiles" @open-file="openKnowledge" />
        </el-tab-pane>

        <el-tab-pane label="工具" name="tools">
          <AgentDetailToolsPanel :tools="tools" :enabled="toolToggles" :saving="toolSaving" @toggle-tool="toggleTool" @save="saveToolToggles" />
        </el-tab-pane>

        <el-tab-pane label="MCP" name="mcps">
          <AgentDetailMcpPanel :mcps="mcps" :enabled="mcpToggles" :saving="mcpSaving" @toggle-mcp="toggleMcp" @save="saveMcpToggles" />
        </el-tab-pane>
      </el-tabs>
    </WorkspacePanel>

    <AgentDetailKnowledgeDialog
      v-model:open="knowledgeDialogOpen"
      :path="activeKnowledgePath"
      :content="content"
      :dirty="content !== originalContent"
      :saving="saving"
      :err="err"
      @update:content="content = $event"
      @save="saveActiveFile"
      @reset="resetContent"
      @copy="copyContent"
    />
  </div>
</template>

<script setup lang="ts">
import WorkspacePanel from '../components/common/WorkspacePanel.vue'
import AgentDetailFilesPanel from '../components/agents/AgentDetailFilesPanel.vue'
import AgentDetailSkillsPanel from '../components/agents/AgentDetailSkillsPanel.vue'
import AgentDetailKnowledgePanel from '../components/agents/AgentDetailKnowledgePanel.vue'
import AgentDetailToolsPanel from '../components/agents/AgentDetailToolsPanel.vue'
import AgentDetailMcpPanel from '../components/agents/AgentDetailMcpPanel.vue'
import AgentDetailKnowledgeDialog from '../components/agents/AgentDetailKnowledgeDialog.vue'
import { useAgentDetail } from '../composables/useAgentDetail'

const {
  agentId,
  agent,
  activeSection,
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
  openKnowledge,
  saveSkillConfig,
  saveToolToggles,
  saveMcpToggles,
  toggleSkillPoolCode,
  toggleTool,
  toggleMcp,
  router,
} = useAgentDetail()
</script>

<style scoped>
.shell {
  height: 100%;
}
.shell :deep(.el-button) {
  box-shadow: none;
}
.shell :deep(.el-button:not(.el-button--primary):not(.el-button--danger)) {
  --el-button-bg-color: var(--ah-surface-soft);
  --el-button-border-color: transparent;
  --el-button-text-color: var(--ah-text-primary);
}
.detailTabs {
  min-height: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
}
.detailTabs :deep(.el-tabs__content) {
  min-height: 0;
  height: calc(100vh - 220px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.detailTabs :deep(.el-tab-pane) {
  min-height: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}
.tabHint {
  margin-bottom: 10px;
  color: var(--ah-text-tertiary);
  font-size: 12px;
}
.shell :deep(.el-switch) {
  --el-switch-on-color: color-mix(in srgb, var(--ah-text-strong) 42%, transparent);
  --el-switch-off-color: var(--ah-border-strong);
}
@media (max-width: 1100px) {
  .detailTabs :deep(.el-tabs__content) {
    height: auto;
  }
}
</style>
