<template>
  <div class="cardGrid">
    <el-card v-for="tool in tools" :key="tool.code" class="itemCard" shadow="never">
      <div class="cardTop">
        <div>
          <div class="cardTitle">{{ tool.name }}</div>
          <div class="cardDesc">{{ tool.code }}</div>
        </div>
        <el-switch :model-value="!!enabled[tool.code]" @change="$emit('toggle-tool', tool.code, Boolean($event))" />
      </div>
      <div class="cardDesc">{{ tool.description || '内置工具' }}</div>
    </el-card>
    <el-card class="configCard" shadow="never">
      <div class="cardTitle">保存工具开关</div>
      <div class="cardDesc">提交当前工具启用状态到 `tools.json`。</div>
      <el-button class="cardButton" :loading="saving" @click="$emit('save')">保存</el-button>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import type { Tool } from '../../api/agents'

defineProps<{
  tools: Tool[]
  enabled: Record<string, boolean>
  saving: boolean
}>()

defineEmits<{
  (e: 'toggle-tool', code: string, checked: boolean): void
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
.configCard {
  padding: 14px;
  background: var(--ah-surface-soft);
}
.cardButton {
  margin-top: 12px;
}
</style>
