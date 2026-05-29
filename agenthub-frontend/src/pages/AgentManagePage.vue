<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import {
  createAgentInstance,
  getMe,
  listAgentInstances,
  listAgentProfiles,
  listGroups,
  type AgentInstance,
  type AgentProfile,
  type Group,
} from '@/services/agenthubService'

type AgentInstanceFormState = {
  group_id: string
  profile_id: string
  display_name: string
  description: string
  base_url: string
  api_key_ref: string
  config_json: string
  status: string
}

const router = useRouter()
const loading = ref(false)
const instanceDialogVisible = ref(false)

const groups = ref<Group[]>([])
const profiles = ref<AgentProfile[]>([])
const instances = ref<AgentInstance[]>([])
const selectedProfileId = ref('')

const instanceForm = reactive<AgentInstanceFormState>({
  group_id: '',
  profile_id: '',
  display_name: '',
  description: '',
  base_url: '',
  api_key_ref: '',
  config_json: '{}',
  status: 'active',
})

const selectedProfile = computed(() => profiles.value.find((item) => item.id === selectedProfileId.value) ?? null)
const profileInstances = computed(() =>
  instances.value.filter((item) => !selectedProfileId.value || item.profile_id === selectedProfileId.value),
)

function resetInstanceForm() {
  instanceForm.group_id = groups.value[0]?.id ?? ''
  instanceForm.profile_id = selectedProfileId.value || profiles.value[0]?.id || ''
  instanceForm.display_name = ''
  instanceForm.description = ''
  instanceForm.base_url = ''
  instanceForm.api_key_ref = ''
  instanceForm.config_json = '{}'
  instanceForm.status = 'active'
}

async function loadAll() {
  const [groupRows, profileRows, instanceRows] = await Promise.all([
    listGroups(),
    listAgentProfiles(),
    listAgentInstances(),
  ])
  groups.value = groupRows
  profiles.value = profileRows
  instances.value = instanceRows
  if (!selectedProfileId.value && profileRows[0]) {
    selectedProfileId.value = profileRows[0].id
  }
}

async function bootstrap() {
  loading.value = true
  try {
    await getMe()
    await loadAll()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : String(error))
  } finally {
    loading.value = false
  }
}

async function submitInstance() {
  if (!instanceForm.group_id || !instanceForm.profile_id || !instanceForm.display_name.trim()) {
    ElMessage.warning('请填写完整的智能体实例信息')
    return
  }
  loading.value = true
  try {
    const created = await createAgentInstance({
      group_id: Number(instanceForm.group_id),
      profile_id: Number(instanceForm.profile_id),
      display_name: instanceForm.display_name.trim(),
      description: instanceForm.description.trim() || null,
      base_url: instanceForm.base_url.trim() || null,
      api_key_ref: instanceForm.api_key_ref.trim() || null,
      config_json: instanceForm.config_json.trim() || '{}',
      status: instanceForm.status,
    })
    instances.value = [...instances.value, created]
    instanceDialogVisible.value = false
    resetInstanceForm()
    ElMessage.success('智能体实例已创建')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : String(error))
  } finally {
    loading.value = false
  }
}

function openDetail(instanceId: string) {
  void router.push({ name: 'agent-detail', params: { id: instanceId } })
}

watch(instanceDialogVisible, (visible) => {
  if (visible) resetInstanceForm()
})

onMounted(() => {
  void bootstrap()
})
</script>

<template>
  <div class="manage-page">
    <div class="toolbar-card">
      <div class="toolbar-title">智能体管理</div>
      <div class="toolbar-actions">
        <el-select v-model="selectedProfileId" placeholder="选择智能体模板" style="width: 240px">
          <el-option v-for="profile in profiles" :key="profile.id" :label="profile.name" :value="profile.id" />
        </el-select>
        <el-button type="primary" @click="instanceDialogVisible = true">添加智能体</el-button>
      </div>
    </div>

    <div class="summary-grid">
      <div class="summary-card">
        <div class="summary-label">当前模板</div>
        <div class="summary-value">{{ selectedProfile?.name || '未选择' }}</div>
      </div>
      <div class="summary-card">
        <div class="summary-label">模板角色</div>
        <div class="summary-value">{{ selectedProfile?.role || '未配置' }}</div>
      </div>
      <div class="summary-card">
        <div class="summary-label">实例数量</div>
        <div class="summary-value">{{ profileInstances.length }}</div>
      </div>
    </div>

    <div class="list-card">
      <div class="list-head">
        <div class="list-title">智能体列表</div>
        <el-tag type="info" effect="plain">{{ profileInstances.length }}</el-tag>
      </div>

      <div v-if="!profileInstances.length" class="empty-wrap">
        <el-empty description="当前模板下暂无智能体" :image-size="88" />
      </div>

      <div v-else class="instance-grid">
        <button v-for="instance in profileInstances" :key="instance.id" class="instance-card" @click="openDetail(instance.id)">
          <div class="instance-avatar">{{ instance.display_name.slice(0, 2).toUpperCase() }}</div>
          <div class="instance-name">{{ instance.display_name }}</div>
          <div class="instance-sub">{{ instance.status }} · {{ instance.base_url || '本地 / 未配置 Base URL' }}</div>
          <div class="instance-link">点击进入配置 →</div>
        </button>
      </div>
    </div>

    <el-dialog v-model="instanceDialogVisible" title="新建智能体实例" width="560px">
      <el-form label-width="92px">
        <el-form-item label="所属群组">
          <el-select v-model="instanceForm.group_id" placeholder="选择群组" style="width: 100%">
            <el-option v-for="group in groups" :key="group.id" :label="group.name" :value="group.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="关联模板">
          <el-select v-model="instanceForm.profile_id" placeholder="选择模板" style="width: 100%">
            <el-option v-for="profile in profiles" :key="profile.id" :label="profile.name" :value="profile.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="显示名">
          <el-input v-model="instanceForm.display_name" placeholder="例如：后端 Agent" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="instanceForm.description" placeholder="补充实例用途" />
        </el-form-item>
        <el-form-item label="Base URL">
          <el-input v-model="instanceForm.base_url" placeholder="例如：https://api.example.com" />
        </el-form-item>
        <el-form-item label="API Key Ref">
          <el-input v-model="instanceForm.api_key_ref" placeholder="例如：vault://agent/backend" />
        </el-form-item>
        <el-form-item label="配置 JSON">
          <el-input v-model="instanceForm.config_json" type="textarea" :rows="3" placeholder='例如：{"workspace":"local"}' />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="instanceForm.status" style="width: 100%">
            <el-option label="active" value="active" />
            <el-option label="inactive" value="inactive" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="instanceDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitInstance">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.manage-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.toolbar-card,
.list-card,
.summary-card {
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

.toolbar-title {
  font-size: 18px;
  font-weight: 700;
  color: #1f2329;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.summary-card {
  padding: 20px;
}

.summary-label {
  color: rgba(31, 35, 41, 0.48);
  font-size: 13px;
}

.summary-value {
  margin-top: 12px;
  font-size: 24px;
  font-weight: 700;
  color: #1f2329;
}

.list-card {
  padding: 22px 26px;
}

.list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}

.list-title {
  font-size: 16px;
  font-weight: 700;
  color: #1f2329;
}

.instance-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.instance-card {
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 22px;
  background: #fff;
  padding: 20px;
  text-align: left;
}

.instance-avatar {
  width: 52px;
  height: 52px;
  border-radius: 18px;
  display: grid;
  place-items: center;
  color: #fff;
  font-weight: 700;
  background: linear-gradient(135deg, #f39c4a 0%, #ffb866 100%);
}

.instance-name {
  margin-top: 16px;
  font-size: 18px;
  font-weight: 700;
  color: #1f2329;
}

.instance-sub,
.instance-link {
  margin-top: 10px;
  color: rgba(31, 35, 41, 0.56);
  line-height: 1.6;
}

.instance-link {
  color: #c96d21;
}

.empty-wrap {
  display: grid;
  place-items: center;
  min-height: 260px;
}
</style>
