<template>
  <el-card class="workspacePanel" shadow="never">
    <div v-if="title || subtitle || $slots.actions" class="panelHeader">
      <div class="panelHeaderText">
        <div v-if="$slots.header">
          <slot name="header" />
        </div>
        <template v-else>
          <div v-if="title" class="panelTitle">{{ title }}</div>
          <div v-if="subtitle" class="panelSub">{{ subtitle }}</div>
        </template>
      </div>
      <div v-if="$slots.actions" class="panelActions">
        <slot name="actions" />
      </div>
    </div>
    <div class="panelBody">
      <slot />
    </div>
  </el-card>
</template>

<script setup lang="ts">
defineProps<{
  title?: string
  subtitle?: string
}>()
</script>

<style scoped>
.workspacePanel {
  height: 100%;
  min-height: 0;
  background: var(--ah-panel-bg);
  border-radius: 22px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.panelHeader {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px 0;
}
.panelHeaderText {
  min-width: 0;
}
.panelTitle {
  font-size: 18px;
  font-weight: 900;
}
.panelSub {
  margin-top: 4px;
  font-size: 12px;
  color: var(--ah-text-tertiary);
}
.panelActions {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 10px;
}
.panelBody {
  flex: 1;
  min-height: 0;
  padding: 16px 18px 18px;
  display: flex;
  flex-direction: column;
}
</style>
