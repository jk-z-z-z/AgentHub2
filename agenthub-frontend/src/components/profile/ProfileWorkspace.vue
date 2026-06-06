<template>
  <div class="page">
    <div class="pageGrid">
      <WorkspacePanel
        title="基础资料"
        subtitle="会展示在通讯录、聊天成员名片和系统上下文里。"
      >
        <template #actions>
          <el-button type="primary" :loading="savingUser" @click="$emit('save-user')">保存资料</el-button>
        </template>

        <el-descriptions class="summary" :column="2" border size="small">
          <el-descriptions-item label="邮箱">{{ user?.email || '-' }}</el-descriptions-item>
          <el-descriptions-item label="用户名">{{ user?.username || '-' }}</el-descriptions-item>
          <el-descriptions-item label="显示名称">{{ displayNameModel || user?.username || '-' }}</el-descriptions-item>
          <el-descriptions-item label="角色">{{ user?.role || '-' }}</el-descriptions-item>
        </el-descriptions>

        <div class="formGrid">
          <div class="field">
            <div class="label">显示名称</div>
            <el-input v-model="displayNameModel" placeholder="例如：沈涛 / 产品设计搭档" />
          </div>
          <div class="field">
            <div class="label">角色</div>
            <el-input :model-value="user?.role || ''" disabled />
          </div>
          <div class="field">
            <div class="label">邮箱</div>
            <el-input :model-value="user?.email || ''" disabled />
          </div>
          <div class="field">
            <div class="label">用户名</div>
            <el-input :model-value="user?.username || ''" disabled />
          </div>
        </div>

        <div class="field">
          <div class="label">个人简介</div>
          <el-input
            v-model="bioModel"
            type="textarea"
            :rows="5"
            placeholder="介绍你的职责、专长、沟通偏好。"
          />
        </div>
      </WorkspacePanel>

      <WorkspacePanel
        title="用户画像 `PROFILE.md`"
        subtitle="建议写偏好、背景、习惯、技术方向，供私聊智能体长期记忆引用。"
      >
        <template #actions>
          <el-button :loading="savingProfileMd" @click="$emit('save-profile-md')">保存画像</el-button>
        </template>

        <el-alert
          class="tipBox"
          title="建议结构"
          type="info"
          :closable="false"
          description="基本信息 / 技术偏好 / 工作方式 / 不喜欢的回答风格 / 当前重点项目"
          show-icon
        />

        <el-input
          v-model="profileMdModel"
          type="textarea"
          :rows="22"
          placeholder="# 用户档案&#10;&#10;## 基本信息&#10;- 职业：&#10;- 擅长：&#10;&#10;## 偏好&#10;- 回答风格："
        />
      </WorkspacePanel>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { User } from '../../api/users'
import WorkspacePanel from '../common/WorkspacePanel.vue'

defineProps<{
  user: User | null
  savingUser: boolean
  savingProfileMd: boolean
}>()

const displayNameModel = defineModel<string>('displayName', { required: true })
const bioModel = defineModel<string>('bio', { required: true })
const profileMdModel = defineModel<string>('profileMd', { required: true })

defineEmits<{
  (e: 'save-user'): void
  (e: 'save-profile-md'): void
}>()
</script>

<style scoped>
.page {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
  color: var(--ah-text);
}
.pageGrid {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(360px, 0.92fr) minmax(420px, 1.08fr);
  gap: 16px;
}
.summary {
  margin-bottom: 14px;
}
.formGrid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-bottom: 14px;
}
.field {
  display: grid;
  gap: 8px;
  margin-bottom: 14px;
}
.label {
  font-size: 12px;
  font-weight: 800;
  color: var(--ah-text-secondary);
}
.tipBox {
  margin-bottom: 12px;
}
@media (max-width: 1180px) {
  .pageGrid,
  .formGrid {
    grid-template-columns: 1fr;
  }
}
</style>
