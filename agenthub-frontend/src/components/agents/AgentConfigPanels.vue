<template>
  <div class="configWrap">
    <div class="toolPanel">
      <div class="toolTitle">工具启用</div>
      <div class="toolHint">工具为内置能力；智能体仅配置是否启用。</div>
      <el-table
        :data="tools"
        size="small"
        empty-text="暂无内置工具"
        class="toolList"
        height="240"
      >
        <el-table-column label="工具" min-width="220">
          <template #default="{ row }">
            <div class="tName">{{ row.name }}</div>
            <div class="tMeta">{{ row.code }} · {{ row.source_type }}</div>
          </template>
        </el-table-column>
        <el-table-column label="启用" width="100" align="right">
          <template #default="{ row }">
            <el-switch
              :model-value="!!toolToggles[row.code]"
              @change="$emit('toggle-tool', row.code, Boolean($event))"
            />
          </template>
        </el-table-column>
      </el-table>
      <div class="toolActions">
        <el-button size="small" :loading="toolSaving" @click="$emit('save-tools')">
          保存工具开关
        </el-button>
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
          <el-switch
            :model-value="skillConfig.enable_agent_local_skills"
            @change="$emit('update:skill-local-enabled', Boolean($event))"
          />
        </div>
      </div>
      <el-table
        :data="skillPool"
        size="small"
        empty-text="全局 Skill 池为空（请在后端 skill-pool 目录下放置 SKILL.md）"
        class="toolList"
        height="240"
      >
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
              @change="(v: boolean) => $emit('toggle-pool-skill', row.code, v)"
            />
          </template>
        </el-table-column>
      </el-table>
      <div class="toolActions">
        <el-button size="small" :loading="skillSaving" @click="$emit('save-skills')">
          保存技能配置
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { SkillPoolItem, Tool } from '../../api/agents'

defineProps<{
  tools: Tool[]
  toolToggles: Record<string, boolean>
  toolSaving: boolean
  skillPool: SkillPoolItem[]
  skillConfig: { enable_agent_local_skills: boolean; pool_skill_codes: string[] }
  skillSaving: boolean
}>()

defineEmits<{
  (e: 'toggle-tool', code: string, checked: boolean): void
  (e: 'save-tools'): void
  (e: 'update:skill-local-enabled', value: boolean): void
  (e: 'toggle-pool-skill', code: string, checked: boolean): void
  (e: 'save-skills'): void
}>()
</script>

<style scoped>
.configWrap {
  display: contents;
}
.toolPanel {
  border: 1px solid var(--ah-border-soft);
  border-radius: 14px;
  padding: 12px;
  margin-bottom: 12px;
  background: var(--ah-surface-soft);
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
  border: 1px solid var(--ah-border-soft);
  border-radius: 12px;
  padding: 10px;
}
.tName {
  font-weight: 900;
}
.tMeta {
  margin-top: 2px;
  font-size: 12px;
  color: var(--ah-text-tertiary);
}
.toolActions {
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
}
</style>
