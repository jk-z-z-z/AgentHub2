<template>
  <div class="cardGrid">
    <el-card class="configCard" shadow="never">
      <div class="cardTitle">本地技能加载</div>
      <div class="cardDesc">开启后会递归加载该智能体目录下的 `skills/`。</div>
      <div class="cardActionRow">
        <el-switch :model-value="enableLocalSkills" @change="$emit('update:enable-local-skills', Boolean($event))" />
        <el-button size="small" :loading="saving" @click="$emit('save')">保存</el-button>
      </div>
    </el-card>

    <el-card v-for="skill in skills" :key="skill.code" class="itemCard" shadow="never">
      <div class="cardTop">
        <div>
          <div class="cardTitle">{{ skill.name || skill.code }}</div>
          <div class="cardDesc">{{ skill.code }}</div>
        </div>
        <el-switch :model-value="selectedCodes.includes(skill.code)" @change="$emit('toggle-skill', skill.code, Boolean($event))" />
      </div>
      <div class="cardDesc">{{ skill.description || '无描述' }}</div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import type { SkillPoolItem } from '../../api/agents'

defineProps<{
  skills: SkillPoolItem[]
  selectedCodes: string[]
  enableLocalSkills: boolean
  saving: boolean
}>()

defineEmits<{
  (e: 'toggle-skill', code: string, checked: boolean): void
  (e: 'update:enable-local-skills', value: boolean): void
  (e: 'save'): void
}>()
</script>

<style scoped>
.cardGrid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
}
.itemCard,
.configCard {
  border-radius: 16px;
}
.cardTop {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}
.cardTitle {
  font-weight: 900;
}
.cardDesc {
  margin-top: 2px;
  font-size: 12px;
  color: var(--ah-text-tertiary);
}
.cardActionRow {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
}
.configCard {
  padding: 14px;
  background: var(--ah-surface-soft);
}
</style>
