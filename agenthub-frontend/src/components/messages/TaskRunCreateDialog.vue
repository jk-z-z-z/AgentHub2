<template>
  <el-dialog v-model="openModel" title="新建任务Run" width="560px">
    <div style="display:grid; gap:10px">
      <el-input v-model="titleModel" placeholder="Run 标题" />
      <el-input v-model="goalModel" type="textarea" :rows="4" placeholder="任务目标：这次 Run 要解决什么问题" />
      <el-input v-model="nodeTextModel" type="textarea" :rows="6" placeholder="每行一个节点：标题 | role_required | detail" />
      <div style="opacity:0.7; font-size:12px">示例：需求澄清 | manager | 明确目标与分工</div>
    </div>

    <div v-if="createErr" class="err" style="margin-top: 8px">{{ createErr }}</div>

    <template #footer>
      <el-button @click="openModel = false">取消</el-button>
      <el-button type="primary" @click="$emit('create')">创建</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
const openModel = defineModel<boolean>('open', { required: true })
const titleModel = defineModel<string>('title', { required: true })
const goalModel = defineModel<string>('goal', { required: true })
const nodeTextModel = defineModel<string>('nodeText', { required: true })

defineProps<{
  createErr: string
}>()

defineEmits<{
  (e: 'create'): void
}>()
</script>

<style scoped>
.err {
  color: #d92d20;
  font-size: 12px;
}
</style>
