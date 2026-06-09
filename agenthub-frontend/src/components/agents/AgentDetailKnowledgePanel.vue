<template>
  <div class="cardGrid">
    <el-card
      v-for="file in files"
      :key="file.path"
      class="itemCard clickable"
      shadow="never"
      @click="$emit('open-file', file.path)"
    >
      <div class="cardTop">
        <div>
          <div class="cardTitle">{{ file.label }}</div>
          <div class="cardDesc">{{ file.path }}</div>
        </div>
        <el-button size="small">编辑</el-button>
      </div>
      <div class="cardDesc">知识库文件</div>
    </el-card>
    <el-empty v-if="files.length === 0" description="暂无知识库文件" />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  files: Array<{ path: string; label: string }>
}>()

defineEmits<{
  (e: 'open-file', path: string): void
}>()
</script>

<style scoped>
.cardGrid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
}
.itemCard {
  border-radius: 16px;
}
.clickable {
  cursor: pointer;
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
</style>
