<template>
  <div v-if="mcps.length > 0" class="cardGrid">
    <el-card v-for="mcp in mcps" :key="mcp.server_code" class="itemCard" shadow="never">
      <div class="cardTop">
        <div>
          <div class="cardTitle">{{ mcp.name }}</div>
          <div class="cardDesc">{{ mcp.server_code }}</div>
        </div>
        <el-switch :model-value="!!enabled[mcp.server_code]" @change="$emit('toggle-mcp', mcp.server_code, Boolean($event))" />
      </div>
      <div class="cardDesc">{{ mcp.description || '无描述' }}</div>
    </el-card>
    <el-card class="configCard" shadow="never">
      <div class="cardTitle">保存 MCP 开关</div>
      <div class="cardDesc">提交当前 MCP 启用状态到 `mcps.json`。</div>
      <el-button class="cardButton" :loading="saving" @click="$emit('save')">保存</el-button>
    </el-card>
  </div>
  <el-empty v-else description="暂无 MCP" />
</template>

<script setup lang="ts">
import type { MCP } from '../../api/agents'

defineProps<{
  mcps: MCP[]
  enabled: Record<string, boolean>
  saving: boolean
}>()

defineEmits<{
  (e: 'toggle-mcp', code: string, checked: boolean): void
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
