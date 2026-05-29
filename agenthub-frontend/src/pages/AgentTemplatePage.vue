<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import {
  createAgentProfile,
  getMe,
  listAgentProfiles,
  type AgentProfile,
} from '@/services/agenthubService'

type AgentProfileFormState = {
  name: string
  role: string
  description: string
  system_prompt: string
  default_model_json: string
  planning_mode: string
}

const loading = ref(false)
const profileDialogVisible = ref(false)
const profiles = ref<AgentProfile[]>([])
const selectedProfileId = ref('')

const profileForm = reactive<AgentProfileFormState>({
  name: '',
  role: '',
  description: '',
  system_prompt: '',
  default_model_json: '{}',
  planning_mode: '',
})

const selectedProfile = computed(() => profiles.value.find((item) => item.id === selectedProfileId.value) ?? profiles.value[0] ?? null)

function resetProfileForm() {
  profileForm.name = ''
  profileForm.role = ''
  profileForm.description = ''
  profileForm.system_prompt = ''
  profileForm.default_model_json = '{}'
  profileForm.planning_mode = ''
}

async function bootstrap() {
  loading.value = true
  try {
    await getMe()
    profiles.value = await listAgentProfiles()
    if (!selectedProfileId.value && profiles.value[0]) {
      selectedProfileId.value = profiles.value[0].id
    }
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : String(error))
  } finally {
    loading.value = false
  }
}

async function submitProfile() {
  if (!profileForm.name.trim() || !profileForm.role.trim() || !profileForm.system_prompt.trim()) {
    ElMessage.warning('请填写完整的智能体模板信息')
    return
  }
  loading.value = true
  try {
    const created = await createAgentProfile({
      name: profileForm.name.trim(),
      role: profileForm.role.trim(),
      description: profileForm.description.trim() || null,
      system_prompt: profileForm.system_prompt.trim(),
      default_model_json: profileForm.default_model_json.trim() || '{}',
      planning_mode: profileForm.planning_mode.trim() || null,
      is_active: 1,
    })
    profiles.value = [...profiles.value, created]
    selectedProfileId.value = created.id
    profileDialogVisible.value = false
    resetProfileForm()
    ElMessage.success('智能体模板已创建')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : String(error))
  } finally {
    loading.value = false
  }
}

watch(profileDialogVisible, (visible) => {
  if (visible) resetProfileForm()
})

onMounted(() => {
  void bootstrap()
})
</script>

<template>
  <div v-loading="loading" class="template-page">
    <div class="toolbar-card">
      <div class="toolbar-title">智能体模板</div>
      <div class="toolbar-actions">
        <el-button type="primary" @click="profileDialogVisible = true">新增模板</el-button>
      </div>
    </div>

    <div class="workspace-layout">
      <section class="template-list-card">
        <div class="list-head">
          <div class="list-title">模板列表</div>
          <el-tag type="info" effect="plain">{{ profiles.length }}</el-tag>
        </div>

        <div v-if="!profiles.length" class="empty-wrap">
          <el-empty description="还没有智能体模板" :image-size="88" />
        </div>

        <button
          v-for="profile in profiles"
          v-else
          :key="profile.id"
          class="template-item"
          :class="{ active: selectedProfile?.id === profile.id }"
          @click="selectedProfileId = profile.id"
        >
          <div class="template-name">{{ profile.name }}</div>
          <div class="template-role">{{ profile.role }}</div>
        </button>
      </section>

      <section class="template-detail-card">
        <template v-if="selectedProfile">
          <div class="detail-head">
            <div>
              <div class="detail-breadcrumb">模板管理 / {{ selectedProfile.name }}</div>
              <div class="detail-title">{{ selectedProfile.name }}</div>
            </div>
            <el-tag :type="selectedProfile.is_active ? 'success' : 'info'" effect="plain">
              {{ selectedProfile.is_active ? '启用中' : '已停用' }}
            </el-tag>
          </div>

          <div class="detail-section">
            <div class="field-row">
              <div class="field-label">角色</div>
              <div class="field-value">{{ selectedProfile.role }}</div>
            </div>
            <div class="field-row">
              <div class="field-label">描述</div>
              <div class="field-value">{{ selectedProfile.description || '暂无描述' }}</div>
            </div>
            <div class="field-row">
              <div class="field-label">规划模式</div>
              <div class="field-value">{{ selectedProfile.planning_mode || '未配置' }}</div>
            </div>
            <div class="field-row">
              <div class="field-label">默认模型</div>
              <div class="field-value code-block">{{ selectedProfile.default_model_json || '{}' }}</div>
            </div>
          </div>

          <div class="detail-section">
            <div class="section-title">系统提示词</div>
            <div class="prompt-card">{{ selectedProfile.system_prompt }}</div>
          </div>
        </template>

        <div v-else class="empty-wrap">
          <el-empty description="请选择一个模板查看详情" :image-size="88" />
        </div>
      </section>
    </div>

    <el-dialog v-model="profileDialogVisible" title="新建智能体模板" width="560px">
      <el-form label-width="92px">
        <el-form-item label="名称">
          <el-input v-model="profileForm.name" placeholder="例如：后端开发工程师" />
        </el-form-item>
        <el-form-item label="角色">
          <el-input v-model="profileForm.role" placeholder="例如：backend-engineer" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="profileForm.description" placeholder="补充智能体职责" />
        </el-form-item>
        <el-form-item label="系统提示词">
          <el-input v-model="profileForm.system_prompt" type="textarea" :rows="5" placeholder="定义 Agent 行为和边界" />
        </el-form-item>
        <el-form-item label="默认模型">
          <el-input v-model="profileForm.default_model_json" type="textarea" :rows="3" placeholder='例如：{"model":"qwen3-max"}' />
        </el-form-item>
        <el-form-item label="规划模式">
          <el-input v-model="profileForm.planning_mode" placeholder="例如：manual / auto" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="profileDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitProfile">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.template-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.toolbar-card,
.template-list-card,
.template-detail-card {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 24px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
}

.toolbar-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 22px 26px;
}

.toolbar-title,
.detail-title {
  font-size: 18px;
  font-weight: 700;
  color: #1f2329;
}

.workspace-layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 20px;
}

.template-list-card {
  padding: 22px;
}

.list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.list-title,
.section-title {
  font-size: 16px;
  font-weight: 700;
  color: #1f2329;
}

.template-item {
  width: 100%;
  margin-bottom: 10px;
  padding: 16px;
  border: 0;
  border-radius: 18px;
  text-align: left;
  background: transparent;
}

.template-item.active,
.template-item:hover {
  background: #f4efe7;
}

.template-name {
  font-size: 16px;
  font-weight: 700;
  color: #1f2329;
}

.template-role {
  margin-top: 6px;
  color: rgba(31, 35, 41, 0.56);
}

.template-detail-card {
  padding: 24px 28px;
}

.detail-head {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 18px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
}

.detail-breadcrumb {
  color: rgba(31, 35, 41, 0.5);
  font-size: 13px;
}

.detail-title {
  margin-top: 8px;
}

.detail-section {
  padding-top: 22px;
}

.field-row {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 16px;
  padding: 12px 0;
  border-bottom: 1px solid rgba(15, 23, 42, 0.04);
}

.field-label {
  color: rgba(31, 35, 41, 0.5);
}

.field-value {
  color: #1f2329;
  line-height: 1.7;
}

.code-block,
.prompt-card {
  padding: 16px;
  border-radius: 16px;
  background: #f8f6f1;
  border: 1px solid rgba(15, 23, 42, 0.05);
  white-space: pre-wrap;
}

.prompt-card {
  margin-top: 12px;
}

.empty-wrap {
  display: grid;
  place-items: center;
  min-height: 260px;
}
</style>
