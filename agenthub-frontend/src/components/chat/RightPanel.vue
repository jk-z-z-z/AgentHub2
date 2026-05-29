<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import {
  createAgentMember,
  createUserMember,
  deleteMember,
  updateMember,
  type AgentInstance,
} from '@/services/agenthubService'

type PanelMember = {
  id: string
  displayName: string
  kind: 'user' | 'agent' | string
  userRef?: string | null
  agentInstanceId?: string | null
  title?: string | null
}

const props = defineProps<{
  open: boolean
  groupId?: string | null
  conversationTitle?: string
  conversationBadge?: string
  members?: PanelMember[]
  agentInstances?: AgentInstance[]
}>()

const emit = defineEmits<{
  (e: 'members-updated'): void
}>()

const createDialogVisible = ref(false)
const editDialogVisible = ref(false)
const createKind = ref<'user' | 'agent'>('user')
const editingMember = ref<PanelMember | null>(null)

const createForm = reactive({
  display_name: '',
  user_ref: '',
  agent_instance_id: '',
  title: '',
})

const editForm = reactive({
  display_name: '',
  title: '',
})

const availableAgentInstances = computed(() => {
  if (!props.groupId) return props.agentInstances ?? []
  return (props.agentInstances ?? []).filter((item) => item.group_id === props.groupId)
})

function openCreate(kind: 'user' | 'agent') {
  createKind.value = kind
  createForm.display_name = ''
  createForm.user_ref = ''
  createForm.agent_instance_id = availableAgentInstances.value[0]?.id ?? ''
  createForm.title = ''
  createDialogVisible.value = true
}

function openEdit(member: PanelMember) {
  editingMember.value = member
  editForm.display_name = member.displayName
  editForm.title = member.title || ''
  editDialogVisible.value = true
}

async function handleCreate() {
  if (!props.groupId || !createForm.display_name.trim()) {
    ElMessage.warning('请补全成员信息')
    return
  }
  try {
    if (createKind.value === 'user') {
      if (!createForm.user_ref.trim()) {
        ElMessage.warning('请输入用户引用')
        return
      }
      await createUserMember({
        group_id: props.groupId,
        display_name: createForm.display_name.trim(),
        user_ref: createForm.user_ref.trim(),
        title: createForm.title.trim() || null,
      })
    } else {
      if (!createForm.agent_instance_id) {
        ElMessage.warning('请选择 Agent 实例')
        return
      }
      await createAgentMember({
        group_id: props.groupId,
        display_name: createForm.display_name.trim(),
        agent_instance_id: createForm.agent_instance_id,
        title: createForm.title.trim() || null,
      })
    }
    createDialogVisible.value = false
    ElMessage.success('成员已添加')
    emit('members-updated')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : String(error))
  }
}

async function handleEdit() {
  if (!editingMember.value || !editForm.display_name.trim()) {
    ElMessage.warning('请补全成员信息')
    return
  }
  try {
    await updateMember({
      member_id: editingMember.value.id,
      display_name: editForm.display_name.trim(),
      title: editForm.title.trim() || null,
    })
    editDialogVisible.value = false
    ElMessage.success('成员已更新')
    emit('members-updated')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : String(error))
  }
}

async function handleDelete(member: PanelMember) {
  try {
    await ElMessageBox.confirm(`确认移除成员“${member.displayName}”吗？`, '删除成员', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    await deleteMember(member.id)
    ElMessage.success('成员已删除')
    emit('members-updated')
  } catch (error) {
    if (error instanceof Error && error.message.includes('cancel')) return
    if (error instanceof Error) ElMessage.error(error.message)
  }
}
</script>

<template>
  <aside v-if="open" class="right-panel">
    <div class="section">
      <div class="section-title">会话信息</div>
      <div class="info-card">
        <div class="name">{{ conversationTitle || '未选择会话' }}</div>
        <el-tag v-if="conversationBadge" type="info" size="small">{{ conversationBadge }}</el-tag>
      </div>
    </div>

    <div class="section">
      <div class="section-title">群聊成员管理</div>
      <div class="member-card">
        <div class="member-actions">
          <el-button size="small" type="primary" plain @click="openCreate('user')">添加用户</el-button>
          <el-button size="small" type="success" plain @click="openCreate('agent')">添加 Agent</el-button>
        </div>

        <el-empty v-if="!members?.length" description="当前会话暂无成员信息" :image-size="72" />
        <div v-else class="member-list">
          <div v-for="member in members" :key="member.id" class="member-item">
            <div class="member-main">
              <div class="member-name">{{ member.displayName }}</div>
              <div v-if="member.title" class="member-title">{{ member.title }}</div>
            </div>
            <div class="member-side">
              <el-tag :type="member.kind === 'agent' ? 'success' : 'info'" size="small" effect="plain">
                {{ member.kind === 'agent' ? 'Agent' : '用户' }}
              </el-tag>
              <div class="member-ops">
                <el-button link size="small" @click="openEdit(member)">编辑</el-button>
                <el-button link size="small" type="danger" @click="handleDelete(member)">删除</el-button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="section">
      <div class="section-title">右侧扩展区</div>
      <div class="placeholder">
        后续这里接 DAG、节点详情、审批卡片和执行事件流。
      </div>
    </div>

    <el-dialog v-model="createDialogVisible" :title="createKind === 'agent' ? '添加 Agent 成员' : '添加用户成员'" width="420px">
      <el-form label-width="88px">
        <el-form-item label="显示名">
          <el-input v-model="createForm.display_name" placeholder="请输入成员显示名" />
        </el-form-item>
        <el-form-item v-if="createKind === 'user'" label="用户引用">
          <el-input v-model="createForm.user_ref" placeholder="请输入用户 id / 引用" />
        </el-form-item>
        <el-form-item v-else label="Agent 实例">
          <el-select v-model="createForm.agent_instance_id" placeholder="选择 Agent 实例" style="width: 100%">
            <el-option
              v-for="instance in availableAgentInstances"
              :key="instance.id"
              :label="instance.display_name"
              :value="instance.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="角色标题">
          <el-input v-model="createForm.title" placeholder="例如：后端工程师 / 审核 Agent" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">确认</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editDialogVisible" title="编辑成员" width="420px">
      <el-form label-width="88px">
        <el-form-item label="显示名">
          <el-input v-model="editForm.display_name" placeholder="请输入成员显示名" />
        </el-form-item>
        <el-form-item label="角色标题">
          <el-input v-model="editForm.title" placeholder="例如：后端工程师 / 审核 Agent" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleEdit">保存</el-button>
      </template>
    </el-dialog>
  </aside>
</template>

<style scoped>
.right-panel {
  border-left: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(18px);
  padding: 18px 16px;
}

.section + .section {
  margin-top: 20px;
}

.section-title {
  margin-bottom: 10px;
  font-size: 13px;
  font-weight: 700;
  color: rgba(15, 23, 42, 0.6);
}

.info-card,
.member-card,
.placeholder {
  border-radius: 16px;
  padding: 14px;
  background: #fff;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
}

.name {
  margin-bottom: 8px;
  font-weight: 800;
}

.member-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
}

.member-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.member-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
}

.member-item:last-child {
  padding-bottom: 0;
  border-bottom: 0;
}

.member-main {
  min-width: 0;
}

.member-name {
  font-weight: 700;
  color: #0f172a;
}

.member-title {
  margin-top: 4px;
  font-size: 12px;
  color: rgba(15, 23, 42, 0.55);
}

.member-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}

.member-ops {
  display: flex;
  gap: 4px;
}

.placeholder {
  line-height: 1.6;
  color: rgba(15, 23, 42, 0.66);
}
</style>
