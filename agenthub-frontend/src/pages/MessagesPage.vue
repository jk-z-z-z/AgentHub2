<template>
  <div class="shell">
    <section class="convPane">
      <div class="paneHeader">
        <el-input v-model="groupSearch" class="searchInput" placeholder="搜索" clearable>
          <template #prefix>
            <el-icon class="searchIcon">
              <Search />
            </el-icon>
          </template>
        </el-input>
        <button class="addBtn" @click="createOpen = true" aria-label="新建会话">
          <el-icon>
            <CirclePlus />
          </el-icon>
        </button>
      </div>

      <div class="convList">
        <div
          v-for="g in filteredGroups"
          :key="g.id"
          class="convItem"
          :class="{ active: g.id === activeGroupId }"
          @click="selectGroup(g.id)"
        >
          <div class="avatar">{{ avatarText(g.name) }}</div>
          <div class="meta">
            <div class="row1">
              <div class="name">{{ g.name }}</div>
              <div class="time">{{ lastTimeMap[g.id] || '' }}</div>
            </div>
            <div class="row2">
              <div class="preview">{{ lastPreviewMap[g.id] || '' }}</div>
              <div class="badge">{{ g.type === 'project' ? '项目组' : '单聊' }}</div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="chatPane">
      <div class="chatHeader">
        <div class="chatTitle">{{ activeGroup?.name || '选择一个会话' }}</div>
        <div class="chatActions">
          <button
            v-if="activeGroup?.type === 'project'"
            class="iconBtn iconBtnLarge"
            @click="openProjectCode"
            aria-label="查看代码"
          >
            <el-icon>
              <FolderOpened />
            </el-icon>
          </button>
          <button
            v-if="activeGroup?.type === 'project'"
            class="iconBtn iconBtnLarge"
            @click="openTaskPlanner"
            aria-label="任务规划"
          >
            <el-icon>
              <Operation />
            </el-icon>
          </button>
          <button class="iconBtn iconBtnLarge" aria-label="更多操作">
            <el-icon>
              <MoreFilled />
            </el-icon>
          </button>
          <button class="iconBtn" aria-label="搜索">
            <el-icon>
              <Search />
            </el-icon>
          </button>
          <button class="iconBtn" :disabled="!activeGroup" @click="openManage" aria-label="聊天管理">
            <el-icon>
              <Setting />
            </el-icon>
          </button>
        </div>
      </div>

      <div class="chatBody">
        <div v-if="loadingGroups" class="empty">加载中…</div>
        <div v-else-if="!activeGroup" class="empty">从左侧选择会话</div>
        <template v-else>
          <div v-if="messages.length === 0" class="empty">暂无消息</div>
          <div v-for="m in messages" :key="m.id" class="msgRow" :class="sideClass(m)">
            <div class="bubble">
              <div class="msgMeta">{{ senderName(m.sender_member_id) }}</div>
              <div class="msgText">{{ m.content }}</div>
            </div>
          </div>
        </template>
      </div>

      <div class="chatComposer">
        <div class="composerMid">
          <div v-if="canMentionAgents && selectedMentions.size > 0" class="mentionChips">
            <span v-for="id in Array.from(selectedMentions)" :key="id" class="chip">
              @{{ senderName(id) }}
              <button class="chipX" @click="removeMention(id)">×</button>
            </span>
          </div>
          <textarea
            v-model="draft"
            class="input"
            placeholder="输入消息…"
            rows="1"
            @input="onDraftInput"
            @keydown="onDraftKeydown"
          />

          <div v-if="canMentionAgents && mentionSuggestOpen" class="mentionSuggest">
            <div class="msTitle">@ 提示</div>
            <div class="msList">
              <div
                v-for="m in filteredAgentMembers"
                :key="m.id"
                class="msItem"
                @click="pickMention(m.id)"
              >
                <div class="msAvatar">
                  <el-icon>
                    <Monitor />
                  </el-icon>
                </div>
                <div class="msName">{{ m.display_name }}</div>
              </div>
              <div v-if="filteredAgentMembers.length === 0" class="msEmpty">无匹配智能体</div>
            </div>
          </div>
        </div>
        <div class="composerActions">
          <button v-if="canMentionAgents" class="toolBtn" @click="openMention" aria-label="选择要@的智能体">
            @
          </button>
          <button class="sendBtn" :disabled="!canSend" @click="send" aria-label="发送消息">
            <el-icon>
              <ArrowUp />
            </el-icon>
          </button>
        </div>
      </div>
    </section>
  </div>

  <el-dialog v-model="mentionOpen" title="选择要@的智能体" width="420px">
    <div class="mentionList">
      <div v-for="m in agentMembers" :key="m.id" class="mentionItem" @click="toggleMention(m.id)">
        <div class="mAvatar">
          <el-icon>
            <Monitor />
          </el-icon>
        </div>
        <div class="mName">{{ m.display_name }}</div>
        <div class="mCheck">
          <el-icon v-if="selectedMentions.has(m.id)">
            <Select />
          </el-icon>
        </div>
      </div>
      <div v-if="agentMembers.length === 0" style="opacity: 0.6; padding: 8px 2px">该会话没有智能体成员</div>
    </div>
    <template #footer>
      <el-button @click="mentionOpen = false">关闭</el-button>
      <el-button type="primary" @click="mentionOpen = false">确定</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="createOpen" title="新建会话" width="520px">
    <div class="createGrid">
      <el-select v-model="createType" placeholder="会话类型" style="width: 160px">
        <el-option label="项目群聊 (project)" value="project" />
        <el-option label="单聊 (personal)" value="personal" />
      </el-select>
      <el-input v-model="createName" placeholder="会话名称 (group.name)" />
    </div>

    <div style="margin-top: 12px; font-weight: 800">选择成员</div>
    <div class="pickGrid">
      <div class="pickCol" v-if="createType !== 'personal'">
        <div class="pickTitle">用户</div>
        <div class="pickList">
          <div v-for="u in users" :key="u.id" class="pickItem" @click="togglePickUser(u)">
            <div class="pAvatar">{{ (u.display_name || u.username || u.email).slice(0, 1).toUpperCase() }}</div>
            <div class="pName">{{ u.display_name || u.username || u.email }}</div>
            <div class="pCheck">
              <el-icon v-if="pickedUserIds.has(String(u.id))">
                <Select />
              </el-icon>
            </div>
          </div>
        </div>
      </div>
      <div class="pickCol">
        <div class="pickTitle">智能体</div>
        <div class="pickList">
          <div v-for="a in agents" :key="a.id" class="pickItem" @click="togglePickAgent(a)">
            <div class="pAvatar">
              <el-icon>
                <Monitor />
              </el-icon>
            </div>
            <div class="pName">{{ a.display_name }}</div>
            <div class="pCheck">
              <el-icon v-if="pickedAgentIds.has(String(a.id))">
                <Select />
              </el-icon>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div v-if="createType === 'personal'" style="margin-top: 8px; opacity: 0.7; font-size: 12px">
      单聊：只需选择 1 个智能体；创建者会自动作为另一成员加入；无需 @ 也会自动触发该智能体回复。
    </div>

    <div v-if="createErr" class="err" style="margin-top: 8px">{{ createErr }}</div>

    <template #footer>
      <el-button @click="createOpen = false">取消</el-button>
      <el-button type="primary" :loading="creating" @click="createGroup">创建</el-button>
    </template>
  </el-dialog>

  <el-drawer
    v-model="manageOpen"
    title="聊天管理"
    direction="rtl"
    size="520px"
    :show-close="true"
    :close-on-click-modal="true"
    :close-on-press-escape="true"
    destroy-on-close
    @close="manageOpen = false"
  >
    <div class="drawerBody" v-if="activeGroup">
      <div class="drawerSection">
        <div class="secTitle">会话信息</div>
        <div class="kvRow"><span class="k">名称</span><span class="v">{{ activeGroup.name }}</span></div>
        <div class="kvRow"><span class="k">类型</span><span class="v">{{ activeGroup.type }}</span></div>
        <div class="kvRow"><span class="k">ID</span><span class="v">{{ activeGroup.id }}</span></div>
        <div style="display: flex; justify-content: flex-end; margin-top: 10px">
          <el-button type="danger" plain @click="deleteActiveGroup">删除会话</el-button>
        </div>
      </div>

      <div class="drawerSection">
        <div class="secTitle">成员</div>
        <div class="memberList">
          <div v-for="m in members" :key="m.id" class="memberRow">
            <div class="mLeft">
              <div class="mName">{{ m.display_name }}</div>
              <div class="mMeta">{{ m.kind }} · member#{{ m.id }}</div>
            </div>
            <div class="mRight">
              <el-button size="small" type="danger" plain @click="removeMember(m)" :disabled="activeGroup.type === 'personal'">
                移除
              </el-button>
            </div>
          </div>
          <div v-if="members.length === 0" style="opacity: 0.6; padding: 8px 2px">暂无成员</div>
        </div>
        <div style="opacity: 0.65; font-size: 12px; margin-top: 10px">
          说明：`personal` 会话固定 2 人，不支持成员变更；`project` 会话可增删成员。
        </div>
      </div>

      <div class="drawerSection" v-if="activeGroup.type === 'project'">
        <div class="secTitle">添加成员</div>
        <div class="addGrid">
          <el-select v-model="addKind" style="width: 120px">
            <el-option label="用户" value="user" />
            <el-option label="智能体" value="agent" />
          </el-select>
          <el-select v-if="addKind === 'user'" v-model="addUserId" placeholder="选择用户" filterable clearable>
            <el-option v-for="u in users" :key="u.id" :label="u.display_name || u.username || u.email" :value="String(u.id)" />
          </el-select>
          <el-select v-else v-model="addAgentId" placeholder="选择智能体" filterable clearable>
            <el-option v-for="a in agents" :key="a.id" :label="a.display_name" :value="String(a.id)" />
          </el-select>
          <el-button type="primary" :loading="adding" @click="addMember">添加</el-button>
        </div>
        <div v-if="manageErr" class="err" style="margin-top: 8px">{{ manageErr }}</div>
      </div>

      <div class="drawerSection" v-if="activeGroup.type === 'project'">
        <div class="secTitle">长期记忆自动提炼配置</div>
        <div v-if="memoryCfgLoading" style="opacity: 0.7; font-size: 12px">加载配置中…</div>
        <template v-else>
          <div class="kvRow">
            <span class="k">自动提炼</span>
            <span class="v"><el-switch v-model="memoryCfg.enabled" /></span>
          </div>
          <div class="kvRow">
            <span class="k">触发Token</span>
            <span class="v"><el-input-number v-model="memoryCfg.trigger_tokens" :min="200" :step="200" /></span>
          </div>
          <div class="kvRow">
            <span class="k">保留最近</span>
            <span class="v"><el-input-number v-model="memoryCfg.keep_recent_messages" :min="0" :step="1" /></span>
          </div>
          <div class="kvRow">
            <span class="k">最小间隔(s)</span>
            <span class="v"><el-input-number v-model="memoryCfg.min_interval_seconds" :min="0" :step="10" /></span>
          </div>
          <div style="display: flex; gap: 8px; margin-top: 10px">
            <el-button size="small" :loading="memoryCfgSaving" @click="saveMemoryConfig">保存配置</el-button>
            <el-button size="small" :loading="memoryCompressing" type="primary" @click="runMemoryCompressNow">立即提炼</el-button>
            <el-button size="small" @click="loadMemoryStatus">刷新状态</el-button>
          </div>
          <div v-if="memoryStatus" style="margin-top: 10px; font-size: 12px; opacity: 0.75; line-height: 1.6">
            <div>待提炼消息：{{ memoryStatus.pending_message_count }}</div>
            <div>待提炼Token：{{ memoryStatus.pending_tokens }}</div>
            <div>最近压缩到消息ID：{{ memoryStatus.last_message_id }}</div>
            <div>是否达到阈值：{{ memoryStatus.will_trigger ? '是' : '否' }}</div>
          </div>
        </template>
      </div>

      <div class="drawerSection" v-if="activeGroup.type === 'project'">
        <div class="secTitle">群管家配置</div>
        <div v-if="assistantCfgLoading" style="opacity: 0.7; font-size: 12px">加载中…</div>
        <template v-else>
          <div class="kvRow">
            <span class="k">启用</span>
            <span class="v"><el-switch v-model="assistantCfgEnabled" /></span>
          </div>
          <div class="kvRow">
            <span class="k">管家成员</span>
            <span class="v">群内系统角色「管家」</span>
          </div>
          <div class="kvRow">
            <span class="k">Manager ID</span>
            <span class="v">{{ assistantCfg?.manager_member_id || '-' }}</span>
          </div>
          <div style="display: flex; justify-content: flex-end; margin-top: 8px">
            <el-button size="small" :loading="assistantCfgSaving" @click="saveAssistantConfig">保存管家配置</el-button>
          </div>
        </template>
      </div>

    </div>
    <template #footer>
      <div class="drawerFooter">
        <el-button @click="manageOpen = false">关闭</el-button>
      </div>
    </template>
  </el-drawer>

  <el-drawer v-model="taskOpen" title="任务规划" direction="rtl" size="980px">
    <div v-if="activeGroup?.type === 'project'" class="taskShell">
      <section class="taskSidebar">
        <div class="taskToolbar">
          <el-button size="small" type="primary" @click="taskCreateOpen = true">新建 Run</el-button>
          <el-button size="small" @click="loadTaskRuns" :loading="taskRunsLoading">刷新</el-button>
        </div>
        <div class="taskHint">
          只保留最常用的操作：创建 Run、查看节点状态、认领、完成、复核。
        </div>
        <div class="taskRunList">
          <button
            v-for="run in taskRuns"
            :key="run.id"
            class="taskRunItem"
            :class="{ active: String(run.id) === activeRunId }"
            @click="selectTaskRun(String(run.id))"
          >
            <div class="taskRunTop">
              <div class="taskRunTitle">{{ run.title }}</div>
              <div class="taskRunStatus">{{ run.status }}</div>
            </div>
            <div class="taskRunGoal">{{ run.goal_text }}</div>
            <div class="taskRunMeta">{{ new Date(run.created_at).toLocaleDateString() }} · Run #{{ run.id }}</div>
          </button>
          <div v-if="!taskRunsLoading && taskRuns.length === 0" class="taskEmpty">
            还没有 Run，先点“新建 Run”
          </div>
        </div>
      </section>

      <section class="taskMain">
        <template v-if="activeTaskRun">
          <div class="taskHeader">
            <div>
              <div class="taskTitle">{{ activeTaskRun.title }}</div>
              <div class="taskSubtitle">
                {{ activeTaskRun.status }} · {{ activeTaskRun.created_at ? new Date(activeTaskRun.created_at).toLocaleString() : '-' }}
              </div>
            </div>
            <div class="taskStats">
              <div class="taskStat">
                <span>总节点</span>
                <strong>{{ taskNodeStats.total }}</strong>
              </div>
              <div class="taskStat">
                <span>进行中</span>
                <strong>{{ taskNodeStats.running }}</strong>
              </div>
              <div class="taskStat">
                <span>已完成</span>
                <strong>{{ taskNodeStats.completed }}</strong>
              </div>
              <div class="taskStat">
                <span>已阻塞</span>
                <strong>{{ taskNodeStats.blocked }}</strong>
              </div>
            </div>
          </div>

          <div class="taskGoalCard">
            <div class="taskSectionTitle">任务目标</div>
            <div class="taskGoalText">{{ activeTaskRun.goal_text }}</div>
          </div>

          <div class="taskSection">
            <div class="taskSectionHeader">
              <div class="taskSectionTitle">节点列表</div>
              <el-button size="small" :loading="taskNodesLoading" @click="loadTaskRunDetails(activeRunId)">
                刷新节点
              </el-button>
            </div>

            <div v-if="taskNodesLoading" class="taskLoading">加载节点中…</div>
            <div v-else class="taskNodeList">
              <div v-for="node in taskNodes" :key="node.id" class="taskNodeCard" :class="nodeStatusClass(node.status)">
                <div class="taskNodeTop">
                  <div>
                    <div class="taskNodeTitle">{{ node.title }}</div>
                    <div class="taskNodeMeta">{{ node.node_key }} · {{ node.role_required || '未指定角色' }}</div>
                  </div>
                  <span class="taskNodeBadge">{{ taskStatusLabel(node.status) }}</span>
                </div>

                <div class="taskNodeDetail">{{ node.detail || '暂无说明' }}</div>

                <div class="taskNodeInfo">
                  <span>依赖：{{ (node.deps || []).join(', ') || '无' }}</span>
                  <span>负责人：{{ node.assignee_member_id ? senderName(node.assignee_member_id) : '待认领' }}</span>
                  <span>复核：{{ node.manager_review_status }}</span>
                </div>

                <div class="taskNodeActions">
                  <el-button size="small" v-if="node.status === 'pending'" @click="claimNode(node)">认领</el-button>
                  <el-button
                    size="small"
                    type="primary"
                    v-if="node.status === 'running' && isNodeMine(node)"
                    @click="completeNode(node)"
                  >
                    完成
                  </el-button>
                  <el-button
                    size="small"
                    v-if="node.status === 'completed' && node.manager_review_status === 'pending'"
                    @click="reviewNode(node, 'approved')"
                  >
                    复核通过
                  </el-button>
                  <el-button
                    size="small"
                    type="danger"
                    plain
                    v-if="node.status === 'completed' && node.manager_review_status === 'pending'"
                    @click="reviewNode(node, 'rework')"
                  >
                    要求返工
                  </el-button>
                </div>
              </div>
              <div v-if="taskNodes.length === 0" class="taskEmpty">当前 Run 还没有节点</div>
            </div>
          </div>
        </template>

        <div v-else class="taskEmpty taskEmptyMain">暂无可查看的任务 Run，请先新建一个。</div>
      </section>
    </div>
    <div v-else class="drawerBody">
      <div class="empty">仅项目群聊支持任务规划</div>
    </div>
  </el-drawer>

  <el-dialog v-model="taskCreateOpen" title="新建任务Run" width="560px">
    <div style="display:grid; gap:10px">
      <el-input v-model="taskCreateTitle" placeholder="Run 标题" />
      <el-input v-model="taskCreateGoal" type="textarea" :rows="4" placeholder="任务目标：这次 Run 要解决什么问题" />
      <el-input
        v-model="taskCreateNodeText"
        type="textarea"
        :rows="6"
        placeholder="每行一个节点：标题 | role_required | detail"
      />
      <div style="opacity:0.7; font-size:12px">示例：需求澄清 | manager | 明确目标与分工</div>
    </div>
    <template #footer>
      <el-button @click="taskCreateOpen = false">取消</el-button>
      <el-button type="primary" @click="createTaskRunNow">创建</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowUp,
  CirclePlus,
  Monitor,
  MoreFilled,
  Operation,
  FolderOpened,
  Search,
  Select,
  Setting,
} from '@element-plus/icons-vue'
import {
  apiCreateGroup,
  apiCreateMessage,
  apiAddAgentMember,
  apiAddUserMember,
  apiDeleteMember,
  apiDeleteGroup,
  apiGetGroupAssistantConfig,
  apiUpdateGroupAssistantConfig,
  apiCreateGroupTaskRun,
  apiListGroupTaskRuns,
  apiListGroupTaskNodes,
  apiListGroupTaskEvents,
  apiGetGroupTaskGraph,
  apiUpdateGroupTaskDag,
  apiListAgentRunEvents,
  type AgentRunEvent,
  apiClaimGroupTaskNode,
  apiCompleteGroupTaskNode,
  apiReviewGroupTaskNode,
  apiBlockGroupTaskRoleBranch,
  apiUnblockGroupTaskRoleBranch,
  apiGetGroupMemoryCompressorConfig,
  apiGetGroupMemoryCompressorStatus,
  apiListAgents,
  apiListGroups,
  apiListMembers,
  apiListMessages,
  apiListUsers,
  apiRunGroupMemoryCompress,
  apiUpdateGroupMemoryCompressorConfig,
  type Agent,
  type GroupAssistantConfig,
  type Group,
  type GroupTaskEvent,
  type GroupTaskGraph,
  type GroupTaskNode,
  type GroupTaskRun,
  type MemoryCompressorConfig,
  type MemoryCompressorStatus,
  type Member,
  type Message,
  type User,
} from '../api/agenthub'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const route = useRoute()
const draft = ref('')
const groups = ref<Group[]>([])
const loadingGroups = ref(false)
const activeGroupId = ref<string>('')
const members = ref<Member[]>([])
const messages = ref<Message[]>([])
const ws = ref<WebSocket | null>(null)
let loadSeq = 0
let wsSeq = 0

const lastPreviewMap = ref<Record<string, string>>({})
const lastTimeMap = ref<Record<string, string>>({})
const groupSearch = ref('')

const activeGroup = computed(() => groups.value.find((g) => g.id === activeGroupId.value) || null)
const filteredGroups = computed(() => {
  const query = groupSearch.value.trim().toLowerCase()
  if (!query) return groups.value
  return groups.value.filter((group) => {
    const name = (group.name || '').toLowerCase()
    const type = (group.type || '').toLowerCase()
    const preview = (lastPreviewMap.value[group.id] || '').toLowerCase()
    return name.includes(query) || type.includes(query) || preview.includes(query)
  })
})

const canSend = computed(() => Boolean(activeGroup.value) && Boolean(draft.value.trim()))
const canMentionAgents = computed(() => activeGroup.value?.type === 'project')
const MANAGER_NAME = '管家'
const agentMembers = computed(() =>
  members.value
    .filter((m) => m.kind === 'agent' || (m.kind === 'system' && m.display_name === MANAGER_NAME))
    .sort((a, b) => {
      const aManager = a.kind === 'system' && a.display_name === MANAGER_NAME
      const bManager = b.kind === 'system' && b.display_name === MANAGER_NAME
      if (aManager && !bManager) return -1
      if (!aManager && bManager) return 1
      return (a.display_name || '').localeCompare(b.display_name || '', 'zh-Hans-CN')
    }),
)
const mentionSuggestOpen = ref(false)
const mentionQuery = ref('')
const filteredAgentMembers = computed(() => {
  const q = mentionQuery.value.trim().toLowerCase()
  if (!q) return agentMembers.value
  return agentMembers.value.filter((m) => (m.display_name || '').toLowerCase().includes(q))
})

const mentionOpen = ref(false)
const selectedMentions = ref<Set<string>>(new Set())

const createOpen = ref(false)
const createType = ref<'project' | 'personal'>('project')
const createName = ref('')
const creating = ref(false)
const createErr = ref('')
const users = ref<User[]>([])
const agents = ref<Agent[]>([])
const pickedUserIds = ref<Set<string>>(new Set())
const pickedAgentIds = ref<Set<string>>(new Set())

const manageOpen = ref(false)
const taskOpen = ref(false)
const taskGraphOpen = ref(false)
const dagSelectedNodeKey = ref('')
const selectedEdgeId = ref('')
const dagViewportRef = ref<HTMLElement | null>(null)
const dagView = ref({ scale: 1, x: 0, y: 0 })
const manageErr = ref('')
const addKind = ref<'user' | 'agent'>('user')
const addUserId = ref<string>('')
const addAgentId = ref<string>('')
const adding = ref(false)
const memoryCfgLoading = ref(false)
const memoryCfgSaving = ref(false)
const memoryCompressing = ref(false)
const memoryCfg = ref<MemoryCompressorConfig>({
  enabled: true,
  trigger_tokens: 3500,
  keep_recent_messages: 12,
  min_interval_seconds: 60,
})
const memoryStatus = ref<MemoryCompressorStatus | null>(null)
const assistantCfgLoading = ref(false)
const assistantCfgSaving = ref(false)
const assistantCfg = ref<GroupAssistantConfig | null>(null)
const assistantCfgEnabled = computed({
  get: () => (assistantCfg.value?.enabled ?? 0) === 1,
  set: (value: boolean) => {
    if (!assistantCfg.value) return
    assistantCfg.value.enabled = value ? 1 : 0
  },
})
const taskRunsLoading = ref(false)
const taskRuns = ref<GroupTaskRun[]>([])
const activeRunId = ref('')
const activeTaskRun = computed(() => taskRuns.value.find((run) => String(run.id) === String(activeRunId.value)) || null)
const taskNodesLoading = ref(false)
const taskNodes = ref<GroupTaskNode[]>([])
const taskEvents = ref<GroupTaskEvent[]>([])
const taskGraph = ref<GroupTaskGraph | null>(null)
const taskCreateOpen = ref(false)
const taskCreateTitle = ref('')
const taskCreateGoal = ref('')
const taskCreateNodeText = ref('需求澄清与初始计划 | manager')
const branchRole = ref('')
const branchReason = ref('')
const taskDagEditOpen = ref(false)
const taskDagEditText = ref('')
const taskDepsEditOpen = ref(false)
const taskDepsDraft = ref<Array<{ node_key: string; title: string; role_required: string | null; detail: string; deps: string[] }>>([])
const expandedEventIds = ref<Set<string>>(new Set())
const nodeAuditOpen = ref(false)
const auditNode = ref<GroupTaskNode | null>(null)
const agentRunEvents = ref<AgentRunEvent[]>([])
const replayOpen = ref(false)
const replayIndex = ref(0)
const branchReasonByRole = computed(() => {
  const out: Record<string, string> = {}
  for (let i = taskEvents.value.length - 1; i >= 0; i -= 1) {
    const e = taskEvents.value[i]
    if (!e || e.event_type !== 'branch.blocked') continue
    try {
      const payload = JSON.parse(e.payload_json || '{}') as { role_required?: string; reason?: string }
      const role = String(payload.role_required || '').trim()
      if (role && !out[role]) {
        out[role] = String(payload.reason || '').trim()
      }
    } catch {
      // ignore parse error
    }
  }
  return out
})

const taskNodeStats = computed(() => {
  const counts = { total: taskNodes.value.length, pending: 0, running: 0, completed: 0, blocked: 0 }
  for (const node of taskNodes.value) {
    if (node.status === 'pending') counts.pending += 1
    else if (node.status === 'running') counts.running += 1
    else if (node.status === 'completed') counts.completed += 1
    else if (node.status === 'blocked') counts.blocked += 1
  }
  return counts
})

watch(
  () => createType.value,
  (t) => {
    createErr.value = ''
    // personal 只允许选 1 个第二成员，这里直接清空已选用户，避免误选造成 400
    if (t === 'personal') {
      pickedUserIds.value = new Set()
    }
  },
)

function avatarText(name: string) {
  const t = (name || '').trim()
  return t ? t.slice(0, 1) : '群'
}

function taskStatusLabel(status: string) {
  if (status === 'completed') return '已完成'
  if (status === 'running') return '进行中'
  if (status === 'blocked') return '已阻塞'
  return '待处理'
}

function senderName(memberId: string) {
  const mid = String(memberId)
  const m = members.value.find((x) => String(x.id) === mid)
  return m?.display_name || mid
}

function sideClass(m: Message) {
  const sender = members.value.find((x) => String(x.id) === String(m.sender_member_id))
  if (sender?.kind === 'user') return 'right'
  return 'left'
}

function normalizeMessage(raw: Message | Record<string, any>): Message {
  return {
    ...raw,
    id: String(raw.id ?? ''),
    group_id: String(raw.group_id ?? ''),
    sender_member_id: String(raw.sender_member_id ?? ''),
    message_type: String(raw.message_type ?? 'text'),
    content: String(raw.content ?? ''),
    metadata_json: String(raw.metadata_json ?? '{}'),
    created_at: String(raw.created_at ?? ''),
    updated_at: String(raw.updated_at ?? ''),
  }
}

async function loadGroups() {
  loadingGroups.value = true
  try {
    const res = await apiListGroups()
    groups.value = res.data
    const qid = String(route.query.groupId || '').trim()
    const preferred = qid ? groups.value.find((g) => String(g.id) === qid) : null
    if (!activeGroupId.value) {
      if (preferred) await selectGroup(preferred.id)
      else if (groups.value.length > 0 && groups.value[0]) await selectGroup(groups.value[0].id)
    }
  } finally {
    loadingGroups.value = false
  }
}

async function selectGroup(id: string) {
  const seq = ++loadSeq
  activeGroupId.value = id
  const [mRes, msgRes] = await Promise.all([apiListMembers(id), apiListMessages(id, undefined, 50)])
  if (seq !== loadSeq || String(activeGroupId.value) !== String(id)) return
  members.value = mRes.data
  messages.value = msgRes.data.map((item) => normalizeMessage(item))
  selectedMentions.value = new Set()
  mentionSuggestOpen.value = false
  mentionQuery.value = ''
  updatePreview(id)
  connectWs(id)
}

function updatePreview(groupId: string) {
  const last = messages.value.at(-1)
  if (!last) return
  lastPreviewMap.value[groupId] = last.content
  lastTimeMap.value[groupId] = new Date(last.created_at).toLocaleDateString()
}

function connectWs(groupId: string) {
  const seq = ++wsSeq
  if (ws.value) {
    try { ws.value.close() } catch {}
    ws.value = null
  }
  const token = localStorage.getItem('token')
  if (!token) return
  const url = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/groups/${groupId}?token=${encodeURIComponent(token)}`
  const socket = new WebSocket(url)
  const pingTimer = window.setInterval(() => {
    try {
      if (socket.readyState === WebSocket.OPEN) socket.send('ping')
    } catch {}
  }, 15000)
  socket.onopen = () => {
    if (seq !== wsSeq || ws.value !== socket) return
    // Keep the connection alive by sending a tiny ping periodically.
    // Server's ws endpoint currently blocks on receive_text().
    try { socket.send('ping') } catch {}
  }
  socket.onerror = () => {
    // ignore; UI will still work via refresh/load
  }
  socket.onclose = () => {
    if (seq !== wsSeq || ws.value !== socket) return
    try { window.clearInterval(pingTimer) } catch {}
    // Best-effort auto-reconnect
    setTimeout(() => {
      if (String(activeGroupId.value) === String(groupId)) connectWs(groupId)
    }, 800)
  }
  socket.onmessage = (evt) => {
    if (seq !== wsSeq || ws.value !== socket) return
    try {
      const payload = JSON.parse(evt.data) as { event?: string; data?: any }
      if (payload.event === 'message.created') {
        const msg = normalizeMessage(payload.data as Record<string, any>)
        if (String(msg.group_id) === String(groupId) && String(activeGroupId.value) === String(groupId)) {
          if (!messages.value.some((m) => String(m.id) === String(msg.id))) {
            messages.value = [...messages.value, msg]
          }
          updatePreview(groupId)
        }
      } else if (payload.event === 'reply.failed') {
        const data = (payload.data || {}) as Record<string, any>
        if (String(data.group_id || '') === String(groupId) && String(activeGroupId.value) === String(groupId)) {
          const errText = String(data.error || 'unknown error')
          ElMessage.error(`AI回复失败：${errText}`)
          const systemMsg = normalizeMessage({
            id: `local-reply-failed-${Date.now()}`,
            group_id: groupId,
            sender_member_id: 'system',
            message_type: 'system',
            content: `系统提示：AI 回复失败（${errText}）`,
            metadata_json: '{}',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          })
          messages.value = [...messages.value, systemMsg]
          updatePreview(groupId)
        }
      }
    } catch {
      // ignore
    }
  }
  ws.value = socket
}

async function send() {
  if (!activeGroup.value) return
  const userMember = members.value.find((m) => m.kind === 'user')
  if (!userMember) return
  const text = draft.value.trim()
  if (!text) return

  const mentionIds = new Set<string>(selectedMentions.value)
  for (const m of agentMembers.value) {
    const name = (m.display_name || '').trim()
    if (!name) continue
    if (text.includes(`@${name}`)) mentionIds.add(String(m.id))
  }
  const meta =
    mentionIds.size > 0
      ? JSON.stringify({
          mentions: Array.from(mentionIds).map((id) => ({ kind: 'agent', member_id: id })),
        })
      : '{}'

  draft.value = ''
  const res = await apiCreateMessage({
    group_id: activeGroup.value.id,
    sender_member_id: userMember.id,
    message_type: 'text',
    content: text,
    metadata_json: meta,
  })
  // Optimistic append: even if WS is disconnected, show the sent message immediately.
  const created = normalizeMessage(res.data)
  if (!messages.value.some((m) => String(m.id) === String(created.id))) {
    messages.value = [...messages.value, created]
    updatePreview(activeGroup.value.id)
  }
  selectedMentions.value = new Set()
}

function openMention() {
  mentionOpen.value = true
}

function toggleMention(memberId: string) {
  const next = new Set(selectedMentions.value)
  if (next.has(memberId)) next.delete(memberId)
  else next.add(memberId)
  selectedMentions.value = next
}

function removeMention(memberId: string) {
  const next = new Set(selectedMentions.value)
  next.delete(memberId)
  selectedMentions.value = next
}

function onDraftInput() {
  if (!canMentionAgents.value) return
  // Minimal mention detection: only consider the last token (cursor-at-end).
  const text = draft.value
  const last = text.split(/\s/).at(-1) || ''
  if (last.startsWith('@')) {
    mentionSuggestOpen.value = true
    mentionQuery.value = last.slice(1)
  } else {
    mentionSuggestOpen.value = false
    mentionQuery.value = ''
  }
}

function onDraftKeydown(event: KeyboardEvent) {
  if (event.key !== 'Enter' || event.shiftKey || event.isComposing) return
  event.preventDefault()
  void send()
}

function pickMention(memberId: string) {
  const m = agentMembers.value.find((x) => x.id === memberId)
  if (!m) return
  const next = new Set(selectedMentions.value)
  next.add(memberId)
  selectedMentions.value = next

  // Replace the last "@xxx" token with "@DisplayName "
  const parts = draft.value.split(/\s/)
  if (parts.length > 0) {
    const last = parts.at(-1) || ''
    if (last.startsWith('@')) {
      parts[parts.length - 1] = `@${m.display_name}`
      draft.value = parts.join(' ') + ' '
    }
  }
  mentionSuggestOpen.value = false
  mentionQuery.value = ''
}

function openManage() {
  manageErr.value = ''
  addUserId.value = ''
  addAgentId.value = ''
  manageOpen.value = true
  if (activeGroup.value?.type === 'project') {
    void loadMemoryConfig()
    void loadMemoryStatus()
    void loadAssistantConfig()
    void loadTaskRuns()
  }
}

function openTaskPlanner() {
  if (!activeGroup.value || activeGroup.value.type !== 'project') return
  taskOpen.value = true
  void loadTaskRuns()
}

function openDagGraphPanel() {
  if (!activeGroup.value || activeGroup.value.type !== 'project') return
  taskGraphOpen.value = true
  void nextTick(() => fitDagView())
}

async function loadAssistantConfig() {
  if (!activeGroup.value || activeGroup.value.type !== 'project') return
  assistantCfgLoading.value = true
  try {
    const res = await apiGetGroupAssistantConfig(activeGroup.value.id)
    assistantCfg.value = res.data
  } catch (error) {
    assistantCfg.value = null
    manageErr.value = error instanceof Error ? error.message : String(error)
  } finally {
    assistantCfgLoading.value = false
  }
}

async function saveAssistantConfig() {
  if (!activeGroup.value || activeGroup.value.type !== 'project') return
  assistantCfgSaving.value = true
  manageErr.value = ''
  try {
    const res = await apiUpdateGroupAssistantConfig(activeGroup.value.id, {
      enabled: assistantCfg.value?.enabled ? 1 : 0,
    })
    assistantCfg.value = res.data
    ElMessage.success('管家配置已保存')
  } catch (e) {
    manageErr.value = e instanceof Error ? e.message : String(e)
  } finally {
    assistantCfgSaving.value = false
  }
}

async function loadTaskRuns() {
  if (!activeGroup.value || activeGroup.value.type !== 'project') return
  taskRunsLoading.value = true
  try {
    const res = await apiListGroupTaskRuns(activeGroup.value.id)
    taskRuns.value = res.data
    if (activeRunId.value && !taskRuns.value.some((r) => String(r.id) === String(activeRunId.value))) {
      activeRunId.value = ''
    }
    if (!activeRunId.value && taskRuns.value[0]) {
      activeRunId.value = String(taskRuns.value[0].id)
    }
    if (activeRunId.value) {
      await loadTaskRunDetails(activeRunId.value)
    } else {
      taskNodes.value = []
      taskEvents.value = []
    }
  } catch (error) {
    taskRuns.value = []
    taskNodes.value = []
    taskEvents.value = []
    taskGraph.value = null
    manageErr.value = error instanceof Error ? error.message : String(error)
  } finally {
    taskRunsLoading.value = false
  }
}

async function loadTaskRunDetails(runId: string) {
  if (!runId) return
  taskNodesLoading.value = true
  try {
    const nodesRes = await apiListGroupTaskNodes(runId)
    taskNodes.value = nodesRes.data
  } catch (error) {
    taskNodes.value = []
    manageErr.value = error instanceof Error ? error.message : String(error)
  } finally {
    taskNodesLoading.value = false
  }
}

async function selectTaskRun(runId: string) {
  activeRunId.value = String(runId)
  await loadTaskRunDetails(activeRunId.value)
}

function openDagEditor() {
  const lines = taskNodes.value.map(
    (n) => `${n.node_key} | ${n.title} | ${n.role_required || ''} | ${n.detail || ''} | ${(n.deps || []).join(',')}`,
  )
  taskDagEditText.value = lines.join('\n')
  taskDagEditOpen.value = true
}

async function saveDagEdit() {
  if (!activeRunId.value) return
  const lines = taskDagEditText.value
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean)
  const nodes = lines.map(parseNodeLine)
  const err = validateDagNodes(nodes)
  if (err) {
    manageErr.value = err
    ElMessage.error(err)
    return
  }
  try {
    await apiUpdateGroupTaskDag(activeRunId.value, nodes)
    taskDagEditOpen.value = false
    await loadTaskRunDetails(activeRunId.value)
    ElMessage.success('DAG 已更新（仅影响未完成节点）')
  } catch (e) {
    manageErr.value = e instanceof Error ? e.message : String(e)
  }
}

function openDepsEditor() {
  taskDepsDraft.value = taskNodes.value.map((n) => ({
    node_key: n.node_key,
    title: n.title,
    role_required: n.role_required || null,
    detail: n.detail || '',
    deps: [...(n.deps || [])],
  }))
  taskDepsEditOpen.value = true
}

async function saveDepsEditor() {
  if (!activeRunId.value) return
  const nodes = taskDepsDraft.value.map((n) => ({
    node_key: n.node_key,
    title: n.title,
    role_required: n.role_required,
    detail: n.detail,
    deps: n.deps,
  }))
  const err = validateDagNodes(nodes)
  if (err) {
    manageErr.value = err
    ElMessage.error(err)
    return
  }
  try {
    await apiUpdateGroupTaskDag(activeRunId.value, nodes)
    taskDepsEditOpen.value = false
    await loadTaskRunDetails(activeRunId.value)
    ElMessage.success('依赖关系已更新')
  } catch (e) {
    manageErr.value = e instanceof Error ? e.message : String(e)
    ElMessage.error(manageErr.value)
  }
}

function parseNodeLine(line: string, idx: number) {
  const parts = line.split('|').map((s) => s.trim()).filter(Boolean)
  // New format: node_key | title | role_required | detail | deps
  // Backward compatible:
  // - title | role_required | detail | deps
  // - title | role_required | detail
  const hasExplicitKey = parts.length >= 5
  const nodeKey = hasExplicitKey ? (parts[0] || `n${idx + 1}`) : `n${idx + 1}`
  const title = hasExplicitKey ? (parts[1] || `节点${idx + 1}`) : (parts[0] || `节点${idx + 1}`)
  const roleRequired = hasExplicitKey ? (parts[2] || null) : (parts[1] || null)
  const detail = hasExplicitKey ? (parts[3] || '') : (parts[2] || '')
  const depsRaw = hasExplicitKey ? (parts[4] || '') : (parts[3] || '')
  const deps = depsRaw
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
  return {
    node_key: nodeKey,
    title,
    detail,
    role_required: roleRequired,
    deps,
  }
}

function validateDagNodes(nodes: Array<{ node_key: string; deps: string[] }>): string | null {
  if (nodes.length === 0) return 'DAG 不能为空'
  const keySet = new Set<string>()
  for (const n of nodes) {
    const key = String(n.node_key || '').trim()
    if (!key) return '存在空的 node_key'
    if (keySet.has(key)) return `重复的 node_key: ${key}`
    keySet.add(key)
  }
  for (const n of nodes) {
    const key = String(n.node_key || '').trim()
    for (const d of n.deps || []) {
      if (d === key) return `节点 ${key} 不能依赖自己`
      if (!keySet.has(d)) return `节点 ${key} 依赖了不存在的节点 ${d}`
    }
  }
  const graph = new Map<string, string[]>()
  for (const n of nodes) graph.set(n.node_key, [...(n.deps || [])])
  const visiting = new Set<string>()
  const visited = new Set<string>()
  const dfs = (k: string): boolean => {
    if (visited.has(k)) return false
    if (visiting.has(k)) return true
    visiting.add(k)
    for (const d of graph.get(k) || []) {
      if (dfs(d)) return true
    }
    visiting.delete(k)
    visited.add(k)
    return false
  }
  for (const n of nodes) {
    if (dfs(n.node_key)) return 'DAG 存在循环依赖'
  }
  return null
}

async function createTaskRunNow() {
  if (!activeGroup.value) return
  const me = members.value.find((m) => m.kind === 'user')
  if (!me) {
    manageErr.value = '当前会话缺少用户成员'
    return
  }
  const title = taskCreateTitle.value.trim()
  const goal = taskCreateGoal.value.trim()
  if (!title || !goal) {
    manageErr.value = '请输入任务标题与目标'
    return
  }
  const lines = taskCreateNodeText.value
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean)
  const nodes = (lines.length > 0 ? lines : ['需求澄清与初始计划 | manager']).map(parseNodeLine)
  try {
    const res = await apiCreateGroupTaskRun({
      group_id: activeGroup.value.id,
      creator_member_id: me.id,
      title,
      goal_text: goal,
      nodes,
    })
    taskCreateOpen.value = false
    taskCreateTitle.value = ''
    taskCreateGoal.value = ''
    taskCreateNodeText.value = '需求澄清与初始计划 | manager'
    await loadTaskRuns()
    if (res.data?.id) {
      activeRunId.value = String(res.data.id)
      await loadTaskRunDetails(activeRunId.value)
    } else if (activeRunId.value) {
      await loadTaskRunDetails(activeRunId.value)
    }
    ElMessage.success('任务运行已创建')
  } catch (e) {
    manageErr.value = e instanceof Error ? e.message : String(e)
  }
}

function isNodeMine(node: GroupTaskNode) {
  const me = members.value.find((m) => m.kind === 'user')
  return !!me && String(node.assignee_member_id || '') === String(me.id)
}

function nodeStatusClass(status: string) {
  if (status === 'completed') return 'statusDone'
  if (status === 'running') return 'statusRun'
  if (status === 'blocked') return 'statusBlocked'
  return 'statusPending'
}

function blockedReason(node: GroupTaskNode) {
  const role = String(node.role_required || '').trim()
  if (!role) return ''
  return branchReasonByRole.value[role] || ''
}

function toggleEventExpand(id: string) {
  const next = new Set(expandedEventIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  expandedEventIds.value = next
}

function expandAllEvents() {
  expandedEventIds.value = new Set(taskEvents.value.map((e) => String(e.id)))
}

function collapseAllEvents() {
  expandedEventIds.value = new Set()
}

function isEventExpanded(id: string) {
  return expandedEventIds.value.has(String(id))
}

function prettyEventPayload(payloadJson: string) {
  try {
    return JSON.stringify(JSON.parse(payloadJson || '{}'), null, 2)
  } catch {
    return payloadJson || '{}'
  }
}

const auditEvents = computed(() => {
  if (!auditNode.value) return [] as GroupTaskEvent[]
  const nid = String(auditNode.value.id)
  return taskEvents.value.filter((e) => String(e.node_id || '') === nid)
})

const nodeExecEvents = computed(() => {
  const prefixes = ['node.exec.']
  return auditEvents.value.filter((e) => prefixes.some((p) => String(e.event_type || '').startsWith(p)))
})

const agentRunTraceEvents = computed(() => {
  return agentRunEvents.value
})

function openNodeAudit(node: GroupTaskNode) {
  auditNode.value = node
  nodeAuditOpen.value = true
  agentRunEvents.value = []
  const rid = String((node as any).agent_run_id || '').trim()
  if (rid) {
    void (async () => {
      try {
        const res = await apiListAgentRunEvents(rid)
        agentRunEvents.value = res.data
      } catch {
        agentRunEvents.value = []
      }
    })()
  }
}

function openRunReplay() {
  replayIndex.value = Math.max(0, taskEvents.value.length - 1)
  replayOpen.value = true
}

function replayStepPrev() {
  replayIndex.value = Math.max(0, replayIndex.value - 1)
}

function replayStepNext() {
  replayIndex.value = Math.min(Math.max(0, taskEvents.value.length - 1), replayIndex.value + 1)
}

const replayCurrentEvent = computed(() => {
  if (taskEvents.value.length === 0) return null
  const i = Math.min(Math.max(0, replayIndex.value), taskEvents.value.length - 1)
  return taskEvents.value[i] || null
})

const replayNodes = computed(() => {
  const base = taskNodes.value.map((n) => ({
    id: String(n.id),
    node_key: n.node_key,
    title: n.title,
    status: 'pending',
    manager_review_status: 'pending',
  }))
  const byId = new Map(base.map((n) => [n.id, n]))
  const max = Math.min(Math.max(0, replayIndex.value), Math.max(0, taskEvents.value.length - 1))
  for (let i = 0; i <= max; i += 1) {
    const e = taskEvents.value[i]
    if (!e) continue
    const nid = String(e.node_id || '')
    const target = byId.get(nid)
    if (!target) continue
    if (e.event_type === 'node.claimed') target.status = 'running'
    if (e.event_type === 'node.completed') target.status = 'completed'
    if (e.event_type === 'node.reviewed' || e.event_type === 'node.auto_reviewed') {
      try {
        const payload = JSON.parse(e.payload_json || '{}') as { manager_review_status?: string; decision?: string }
        const decision = String(payload.manager_review_status || payload.decision || '').trim()
        if (decision === 'rework') {
          target.manager_review_status = 'rework'
          target.status = 'running'
        } else if (decision === 'approved') {
          target.manager_review_status = 'approved'
          target.status = 'completed'
        }
      } catch {
        // ignore parse errors
      }
    }
  }
  return base
})

const dagGraph = computed(() => {
  const rawSnapshot = taskGraph.value?.snapshot_json || '{}'
  let snapshot: any = {}
  try {
    snapshot = JSON.parse(rawSnapshot)
  } catch {
    snapshot = {}
  }
  const snapNodes = Array.isArray(snapshot?.nodes) ? snapshot.nodes : []
  const snapEdges = Array.isArray(snapshot?.edges) ? snapshot.edges : []

  const nodes = taskNodes.value
  if (!nodes.length) return { width: 640, height: 120, nodes: [] as any[], edges: [] as any[] }

  const nodesByKey = new Map(nodes.map((n) => [String(n.node_key), n]))
  const byKey = new Map<string, any>()
  for (const sn of snapNodes) {
    const key = String(sn?.node_key || '').trim()
    if (!key) continue
    const full = nodesByKey.get(key)
    byKey.set(key, full || sn)
  }
  for (const n of nodes) {
    const key = String(n.node_key)
    if (!byKey.has(key)) byKey.set(key, n)
  }

  const indegree = new Map<string, number>()
  const outs = new Map<string, string[]>()
  for (const [k] of byKey.entries()) {
    indegree.set(String(k), 0)
    outs.set(String(k), [])
  }
  const edgesInput: Array<{ from: string; to: string }> = []
  for (const e of snapEdges) {
    const from = String(e?.from || '').trim()
    const to = String(e?.to || '').trim()
    if (!from || !to) continue
    if (!byKey.has(from) || !byKey.has(to)) continue
    edgesInput.push({ from, to })
    outs.get(from)?.push(to)
    indegree.set(to, (indegree.get(to) || 0) + 1)
  }

  const queue: string[] = []
  for (const [k, v] of indegree.entries()) if (v === 0) queue.push(k)
  const level = new Map<string, number>()
  for (const k of queue) level.set(k, 0)
  while (queue.length) {
    const k = queue.shift() as string
    const nextLevel = (level.get(k) || 0) + 1
    for (const to of outs.get(k) || []) {
      level.set(to, Math.max(level.get(to) || 0, nextLevel))
      const left = (indegree.get(to) || 0) - 1
      indegree.set(to, left)
      if (left === 0) queue.push(to)
    }
  }
  for (const k of byKey.keys()) if (!level.has(String(k))) level.set(String(k), 0)
  const columns = new Map<number, any[]>()
  for (const [k, n] of byKey.entries()) {
    const lv = level.get(String(k)) || 0
    const arr = columns.get(lv) || []
    arr.push(n)
    columns.set(lv, arr)
  }
  const colKeys = Array.from(columns.keys()).sort((a, b) => a - b)
  for (const k of colKeys) {
    const arr = columns.get(k) || []
    arr.sort((a, b) => String(a.node_key).localeCompare(String(b.node_key)))
    columns.set(k, arr)
  }
  const NODE_W = 196
  const NODE_H = 92
  const COL_GAP = 120
  const ROW_GAP = 28
  const PAD_X = 18
  const PAD_Y = 18
  const visualNodes: Array<any & { left: number; top: number }> = []
  let maxRows = 1
  for (const k of colKeys) maxRows = Math.max(maxRows, (columns.get(k) || []).length)
  for (const k of colKeys) {
    const arr = columns.get(k) || []
    arr.forEach((n, idx) => {
      visualNodes.push(Object.assign({}, n, { left: PAD_X + k * (NODE_W + COL_GAP), top: PAD_Y + idx * (NODE_H + ROW_GAP) }))
    })
  }
  const pos = new Map(visualNodes.map((n) => [String(n.node_key), n]))
  const edges: Array<{ id: string; from: string; to: string; x1: number; y1: number; x2: number; y2: number }> = []
  for (const e of edgesInput) {
    const from = pos.get(String(e.from))
    const to = pos.get(String(e.to))
    if (!from || !to) continue
    edges.push({
      id: `${e.from}->${e.to}`,
      from: String(e.from),
      to: String(e.to),
      x1: from.left + NODE_W,
      y1: from.top + NODE_H / 2,
      x2: to.left,
      y2: to.top + NODE_H / 2,
    })
  }
  const width = PAD_X * 2 + Math.max(1, colKeys.length) * NODE_W + Math.max(0, colKeys.length - 1) * COL_GAP
  const height = PAD_Y * 2 + maxRows * NODE_H + Math.max(0, maxRows - 1) * ROW_GAP
  return { width, height, nodes: visualNodes, edges }
})

function fitDagView() {
  const viewport = dagViewportRef.value
  if (!viewport || dagGraph.value.width <= 0 || dagGraph.value.height <= 0) return
  const vw = viewport.clientWidth
  const vh = viewport.clientHeight
  const margin = 24
  const sx = (vw - margin * 2) / dagGraph.value.width
  const sy = (vh - margin * 2) / dagGraph.value.height
  const scale = Math.min(1.2, Math.max(0.2, Math.min(sx, sy)))
  const x = Math.max(0, (vw - dagGraph.value.width * scale) / 2)
  const y = Math.max(0, (vh - dagGraph.value.height * scale) / 2)
  dagView.value = { scale, x, y }
}

function resetDagView() {
  dagView.value = { scale: 1, x: 0, y: 0 }
}

watch(
  () => [taskGraphOpen.value, dagGraph.value.width, dagGraph.value.height],
  ([open]) => {
    if (!open) return
    void nextTick(() => fitDagView())
  },
)

const dagReachability = computed(() => {
  const forward = new Map<string, Set<string>>()
  const reverse = new Map<string, Set<string>>()
  const rawSnapshot = taskGraph.value?.snapshot_json || '{}'
  let snapshot: any = {}
  try {
    snapshot = JSON.parse(rawSnapshot)
  } catch {
    snapshot = {}
  }
  const snapNodes = Array.isArray(snapshot?.nodes) ? snapshot.nodes : []
  for (const sn of snapNodes) {
    const key = String(sn?.node_key || '').trim()
    if (!key) continue
    if (!forward.has(key)) forward.set(key, new Set())
    if (!reverse.has(key)) reverse.set(key, new Set())
  }
  for (const e of dagGraph.value.edges) {
    if (!forward.has(e.from)) forward.set(e.from, new Set())
    if (!reverse.has(e.to)) reverse.set(e.to, new Set())
    forward.get(e.from)?.add(e.to)
    reverse.get(e.to)?.add(e.from)
  }
  const selected = String(dagSelectedNodeKey.value || '').trim()
  const upstream = new Set<string>()
  const downstream = new Set<string>()
  if (selected) {
    const stackUp = [selected]
    while (stackUp.length) {
      const cur = stackUp.pop() as string
      for (const prev of reverse.get(cur) || []) {
        if (upstream.has(prev)) continue
        upstream.add(prev)
        stackUp.push(prev)
      }
    }
    const stackDown = [selected]
    while (stackDown.length) {
      const cur = stackDown.pop() as string
      for (const nxt of forward.get(cur) || []) {
        if (downstream.has(nxt)) continue
        downstream.add(nxt)
        stackDown.push(nxt)
      }
    }
  }
  return { selected, upstream, downstream }
})

function selectDagNode(nodeKey: string) {
  const key = String(nodeKey || '').trim()
  if (!key) return
  dagSelectedNodeKey.value = dagSelectedNodeKey.value === key ? '' : key
  selectedEdgeId.value = ''
}

function selectEdge(edgeId: string) {
  const id = String(edgeId || '').trim()
  if (!id) return
  selectedEdgeId.value = selectedEdgeId.value === id ? '' : id
}

const selectedEdgeText = computed(() => {
  const edge = dagGraph.value.edges.find((e) => e.id === selectedEdgeId.value)
  if (!edge) return ''
  return `依赖关系：${edge.from} → ${edge.to}`
})

function isSelectedNode(nodeKey: string) {
  return String(nodeKey) === String(dagReachability.value.selected)
}

function shouldDimNode(nodeKey: string) {
  const selected = dagReachability.value.selected
  if (!selected) return false
  const key = String(nodeKey)
  if (key === selected) return false
  if (dagReachability.value.upstream.has(key)) return false
  if (dagReachability.value.downstream.has(key)) return false
  return true
}

function edgeOpacity(edge: { from: string; to: string }) {
  const selected = dagReachability.value.selected
  if (!selected) return 1
  const onPath =
    (dagReachability.value.upstream.has(edge.from) && (edge.to === selected || dagReachability.value.upstream.has(edge.to))) ||
    (edge.from === selected && dagReachability.value.downstream.has(edge.to)) ||
    (dagReachability.value.downstream.has(edge.from) && dagReachability.value.downstream.has(edge.to)) ||
    (dagReachability.value.upstream.has(edge.from) && edge.to === selected)
  return onPath ? 1 : 0.22
}

function edgeStroke(edge: { from: string; to: string }) {
  const selected = dagReachability.value.selected
  if (!selected) return '#6d86b8'
  const upstreamToSelected = dagReachability.value.upstream.has(edge.from) && (edge.to === selected || dagReachability.value.upstream.has(edge.to))
  const selectedToDownstream = (edge.from === selected || dagReachability.value.downstream.has(edge.from)) && dagReachability.value.downstream.has(edge.to)
  if (upstreamToSelected) return '#f59e0b'
  if (selectedToDownstream) return '#2563eb'
  return '#9aa6bd'
}

function edgeStrokeWidth(edge: { from: string; to: string }) {
  const selected = dagReachability.value.selected
  const base = 1.8
  if (!selected) return base
  const active =
    dagReachability.value.upstream.has(edge.from) ||
    dagReachability.value.downstream.has(edge.from) ||
    edge.from === selected ||
    edge.to === selected
  return active ? 2.4 : 1.5
}

function buildAuditExport() {
  if (!auditNode.value) return null
  return {
    exported_at: new Date().toISOString(),
    node: {
      id: auditNode.value.id,
      node_key: auditNode.value.node_key,
      title: auditNode.value.title,
      status: auditNode.value.status,
      role_required: auditNode.value.role_required,
      deps: auditNode.value.deps || [],
      assignee_member_id: auditNode.value.assignee_member_id,
      manager_review_status: auditNode.value.manager_review_status,
      output_summary: auditNode.value.output_summary,
      updated_at: auditNode.value.updated_at,
    },
    events: auditEvents.value.map((e) => ({
      id: e.id,
      event_type: e.event_type,
      payload_json: e.payload_json,
      created_at: e.created_at,
    })),
  }
}

async function copyAuditJson() {
  const payload = buildAuditExport()
  if (!payload) return
  const text = JSON.stringify(payload, null, 2)
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('审计JSON已复制')
  } catch {
    ElMessage.error('复制失败，请检查浏览器权限')
  }
}

function downloadAuditJson() {
  const payload = buildAuditExport()
  if (!payload || !auditNode.value) return
  const text = JSON.stringify(payload, null, 2)
  const blob = new Blob([text], { type: 'application/json;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `node-audit-${auditNode.value.node_key}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

function buildRunAuditExport() {
  const run = taskRuns.value.find((r) => String(r.id) === String(activeRunId.value))
  if (!run) return null
  return {
    exported_at: new Date().toISOString(),
    group: activeGroup.value
      ? {
          id: activeGroup.value.id,
          name: activeGroup.value.name,
          type: activeGroup.value.type,
        }
      : null,
    run,
    members: members.value.map((m) => ({
      id: m.id,
      kind: m.kind,
      display_name: m.display_name,
      user_ref: m.user_ref,
      agent_instance_id: m.agent_instance_id,
    })),
    nodes: taskNodes.value.map((n) => ({
      id: n.id,
      node_key: n.node_key,
      title: n.title,
      detail: n.detail,
      role_required: n.role_required,
      deps: n.deps || [],
      status: n.status,
      assignee_kind: n.assignee_kind,
      assignee_member_id: n.assignee_member_id,
      manager_review_status: n.manager_review_status,
      output_summary: n.output_summary,
      updated_at: n.updated_at,
    })),
    events: taskEvents.value.map((e) => ({
      id: e.id,
      node_id: e.node_id,
      event_type: e.event_type,
      payload_json: e.payload_json,
      created_at: e.created_at,
    })),
  }
}

async function copyRunAuditJson() {
  const payload = buildRunAuditExport()
  if (!payload) {
    ElMessage.warning('请先选择一个Run')
    return
  }
  const text = JSON.stringify(payload, null, 2)
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('Run审计JSON已复制')
  } catch {
    ElMessage.error('复制失败，请检查浏览器权限')
  }
}

function downloadRunAuditJson() {
  const payload = buildRunAuditExport()
  if (!payload) {
    ElMessage.warning('请先选择一个Run')
    return
  }
  const runId = String(activeRunId.value || 'run')
  const text = JSON.stringify(payload, null, 2)
  const blob = new Blob([text], { type: 'application/json;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `run-audit-${runId}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

async function claimNode(node: GroupTaskNode) {
  const me = members.value.find((m) => m.kind === 'user')
  if (!me) return
  try {
    await apiClaimGroupTaskNode(String(node.id), String(me.id))
    await loadTaskRunDetails(String(node.run_id))
  } catch (e) {
    manageErr.value = e instanceof Error ? e.message : String(e)
  }
}

async function completeNode(node: GroupTaskNode) {
  const summary = window.prompt('请输入节点完成总结（会用于管家复核）') || ''
  if (!summary.trim()) return
  try {
    await apiCompleteGroupTaskNode(String(node.id), summary.trim())
    await loadTaskRunDetails(String(node.run_id))
  } catch (e) {
    manageErr.value = e instanceof Error ? e.message : String(e)
  }
}

async function reviewNode(node: GroupTaskNode, status: 'approved' | 'rework') {
  const note = status === 'rework' ? (window.prompt('请输入返工说明') || '') : ''
  try {
    await apiReviewGroupTaskNode(String(node.id), { manager_review_status: status, note })
    await loadTaskRunDetails(String(node.run_id))
  } catch (e) {
    manageErr.value = e instanceof Error ? e.message : String(e)
  }
}

async function blockBranch() {
  if (!activeRunId.value || !branchRole.value.trim() || !branchReason.value.trim()) return
  try {
    await apiBlockGroupTaskRoleBranch(activeRunId.value, branchRole.value.trim(), branchReason.value.trim())
    await loadTaskRunDetails(activeRunId.value)
    ElMessage.success('已阻塞分支')
  } catch (e) {
    manageErr.value = e instanceof Error ? e.message : String(e)
  }
}

async function unblockBranch() {
  if (!activeRunId.value || !branchRole.value.trim() || !branchReason.value.trim()) return
  try {
    await apiUnblockGroupTaskRoleBranch(activeRunId.value, branchRole.value.trim(), branchReason.value.trim())
    await loadTaskRunDetails(activeRunId.value)
    ElMessage.success('已解除分支阻塞')
  } catch (e) {
    manageErr.value = e instanceof Error ? e.message : String(e)
  }
}

async function loadMemoryConfig() {
  if (!activeGroup.value || activeGroup.value.type !== 'project') return
  memoryCfgLoading.value = true
  try {
    const res = await apiGetGroupMemoryCompressorConfig(activeGroup.value.id)
    memoryCfg.value = res.data
  } catch (e) {
    manageErr.value = e instanceof Error ? e.message : String(e)
  } finally {
    memoryCfgLoading.value = false
  }
}

async function loadMemoryStatus() {
  if (!activeGroup.value || activeGroup.value.type !== 'project') return
  try {
    const res = await apiGetGroupMemoryCompressorStatus(activeGroup.value.id)
    memoryStatus.value = res.data
  } catch (e) {
    manageErr.value = e instanceof Error ? e.message : String(e)
  }
}

async function saveMemoryConfig() {
  if (!activeGroup.value || activeGroup.value.type !== 'project') return
  manageErr.value = ''
  memoryCfgSaving.value = true
  try {
    const res = await apiUpdateGroupMemoryCompressorConfig(activeGroup.value.id, {
      enabled: Boolean(memoryCfg.value.enabled),
      trigger_tokens: Number(memoryCfg.value.trigger_tokens || 0),
      keep_recent_messages: Number(memoryCfg.value.keep_recent_messages || 0),
      min_interval_seconds: Number(memoryCfg.value.min_interval_seconds || 0),
    })
    memoryCfg.value = res.data
    await loadMemoryStatus()
    ElMessage.success('长期记忆自动提炼配置已保存')
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    manageErr.value = msg
    ElMessage.error(msg)
  } finally {
    memoryCfgSaving.value = false
  }
}

async function runMemoryCompressNow() {
  if (!activeGroup.value || activeGroup.value.type !== 'project') return
  manageErr.value = ''
  memoryCompressing.value = true
  try {
    const res = await apiRunGroupMemoryCompress(activeGroup.value.id)
    if (res.data.compressed) {
      ElMessage.success(`提炼完成，压缩 ${res.data.compressed_count || 0} 条消息`)
    } else {
      ElMessage.info(`本次未触发提炼：${res.data.reason || 'no-op'}`)
    }
    await loadMemoryStatus()
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    manageErr.value = msg
    ElMessage.error(msg)
  } finally {
    memoryCompressing.value = false
  }
}

async function openProjectCode() {
  if (!activeGroup.value || activeGroup.value.type !== 'project') return
  await router.push({ name: 'project-code', query: { groupId: activeGroup.value.id } })
}

async function addMember() {
  if (!activeGroup.value) return
  if (activeGroup.value.type !== 'project') return
  manageErr.value = ''
  adding.value = true
  try {
    if (addKind.value === 'user') {
      const id = addUserId.value
      if (!id) {
        manageErr.value = '请选择用户'
        return
      }
      const u = users.value.find((x) => String(x.id) === String(id))
      const label = u?.display_name || u?.username || u?.email || id
      await apiAddUserMember({ group_id: activeGroup.value.id, user_ref: String(id), display_name: label, title: null })
    } else {
      const id = addAgentId.value
      if (!id) {
        manageErr.value = '请选择智能体'
        return
      }
      const a = agents.value.find((x) => String(x.id) === String(id))
      const label = a?.display_name || `Agent#${id}`
      await apiAddAgentMember({ group_id: activeGroup.value.id, agent_instance_id: String(id), display_name: label, title: null })
    }
    const mRes = await apiListMembers(activeGroup.value.id)
    members.value = mRes.data
    addUserId.value = ''
    addAgentId.value = ''
  } catch (e) {
    manageErr.value = e instanceof Error ? e.message : String(e)
  } finally {
    adding.value = false
  }
}

async function removeMember(m: Member) {
  if (!activeGroup.value) return
  if (activeGroup.value.type !== 'project') return
  manageErr.value = ''
  try {
    await apiDeleteMember(m.id)
    const mRes = await apiListMembers(activeGroup.value.id)
    members.value = mRes.data
  } catch (e) {
    manageErr.value = e instanceof Error ? e.message : String(e)
  }
}

async function deleteActiveGroup() {
  if (!activeGroup.value) return
  const g = activeGroup.value
  try {
    await ElMessageBox.confirm(`确认删除会话「${g.name}」？该操作会删除成员与消息记录。`, '删除会话', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  manageErr.value = ''
  try {
    await apiDeleteGroup(g.id)
    ElMessage.success('已删除会话')
    manageOpen.value = false
    activeGroupId.value = ''
    members.value = []
    messages.value = []
    await loadGroups()
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    manageErr.value = msg
    ElMessage.error(msg)
  }
}

onMounted(loadGroups)

onMounted(async () => {
  const [u, a] = await Promise.all([apiListUsers(), apiListAgents()])
  users.value = u.data
  agents.value = a.data
})

onBeforeUnmount(() => {
  try { ws.value?.close() } catch {}
})

function togglePickUser(u: User) {
  const id = String(u.id)
  const next = new Set(pickedUserIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  pickedUserIds.value = next
}

function togglePickAgent(a: Agent) {
  const id = String(a.id)
  const next = new Set(pickedAgentIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  pickedAgentIds.value = next
}

async function createGroup() {
  createErr.value = ''
  const pickedUsers = Array.from(pickedUserIds.value)
  const pickedAgents = Array.from(pickedAgentIds.value)

  if (createType.value === 'personal') {
    // 按产品约束：personal 只选 1 个智能体（创建者自动加入）
    if (pickedUsers.length !== 0 || pickedAgents.length !== 1) {
      createErr.value = '单聊只能选择 1 个智能体（不需要选择用户）'
      return
    }
  }

  let name = createName.value.trim()
  if (!name) {
    if (createType.value === 'personal' && pickedAgents.length === 1) {
      const a = agents.value.find((x) => String(x.id) === pickedAgents[0])
      const label = a?.display_name || `Agent#${pickedAgents[0]}`
      name = `与${label}的单聊`
    } else {
      createErr.value = '请输入会话名称'
      return
    }
  }

  creating.value = true
  try {
    await apiCreateGroup({
      name,
      description: null,
      type: createType.value,
      users: pickedUsers.map((id) => {
        const u = users.value.find((x) => String(x.id) === id)
        const label = u?.display_name || u?.username || u?.email || id
        return { user_id: String(id), display_name: label, title: null }
      }),
      agents: pickedAgents.map((id) => {
        const a = agents.value.find((x) => String(x.id) === id)
        const label = a?.display_name || `Agent#${id}`
        return { agent_id: String(id), display_name: label, title: null }
      }),
    })
    createOpen.value = false
    createName.value = ''
    pickedUserIds.value = new Set()
    pickedAgentIds.value = new Set()
    await loadGroups()
  } catch (e) {
    createErr.value = e instanceof Error ? e.message : String(e)
  } finally {
    creating.value = false
  }
}
</script>

<style scoped>
.shell {
  height: calc(100vh - 36px);
  display: grid;
  grid-template-columns: 340px minmax(0, 1fr);
  gap: 12px;
  align-items: stretch;
}

.convPane,
.chatPane {
  background: rgba(255, 255, 255, 0.84);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 18px;
  overflow: hidden;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.paneHeader {
  height: 64px;
  padding: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid rgba(31, 35, 41, 0.06);
}
.searchInput {
  flex: 1;
}
.searchInput :deep(.el-input__wrapper) {
  height: 38px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: none;
}
.searchInput :deep(.el-input__prefix-inner) {
  color: rgba(31, 35, 41, 0.42);
}
.searchIcon {
  font-size: 18px;
}
.addBtn {
  width: 38px;
  height: 38px;
  border: 0;
  border-radius: 12px;
  cursor: pointer;
  background: transparent;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: rgba(31, 35, 41, 0.88);
}
.addBtn:hover {
  background: rgba(31, 35, 41, 0.06);
}

.convList {
  padding: 8px;
  display: grid;
  gap: 6px;
  overflow: auto;
  max-height: calc(100% - 60px);
}
.convItem {
  display: grid;
  grid-template-columns: 52px 1fr;
  gap: 10px;
  padding: 12px 10px;
  border-radius: 14px;
  cursor: pointer;
}
.convItem:hover {
  background: rgba(79, 140, 255, 0.06);
}
.convItem.active {
  background: rgba(79, 140, 255, 0.12);
}
.avatar {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #4f8cff, #7aa8ff);
  color: #fff;
  font-weight: 800;
  font-size: 16px;
}
.meta .row1 {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.name {
  font-weight: 800;
  font-size: 16px;
}
.time {
  font-size: 12px;
  opacity: 0.55;
}
.row2 {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 5px;
}
.preview {
  font-size: 13px;
  opacity: 0.66;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.badge {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(79, 140, 255, 0.14);
  color: #2563eb;
  font-weight: 700;
  white-space: nowrap;
}

.drawerBody {
  padding: 10px 14px;
}
.drawerFooter {
  display: flex;
  justify-content: flex-end;
  width: 100%;
  padding: 0 14px 14px;
  box-sizing: border-box;
}
.taskShell {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 12px;
  height: calc(100% - 12px);
  min-height: 0;
}
.taskSidebar,
.taskMain {
  min-width: 0;
  border: 1px solid rgba(31, 35, 41, 0.06);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.76);
}
.taskSidebar {
  display: flex;
  flex-direction: column;
  padding: 12px;
}
.taskToolbar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.taskHint {
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(79, 140, 255, 0.08);
  color: rgba(31, 35, 41, 0.68);
  font-size: 12px;
  line-height: 1.5;
}
.taskRunList {
  margin-top: 12px;
  display: grid;
  gap: 10px;
  overflow: auto;
}
.taskRunItem {
  width: 100%;
  text-align: left;
  border: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 14px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.92);
  cursor: pointer;
}
.taskRunItem:hover {
  border-color: rgba(79, 140, 255, 0.2);
  background: rgba(79, 140, 255, 0.05);
}
.taskRunItem.active {
  border-color: rgba(79, 140, 255, 0.32);
  background: rgba(79, 140, 255, 0.1);
}
.taskRunTop {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.taskRunTitle,
.taskTitle {
  font-size: 16px;
  font-weight: 900;
}
.taskRunStatus,
.taskNodeBadge {
  flex: 0 0 auto;
  font-size: 12px;
  font-weight: 800;
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(31, 35, 41, 0.06);
}
.taskRunGoal {
  margin-top: 8px;
  font-size: 12px;
  line-height: 1.5;
  color: rgba(31, 35, 41, 0.72);
}
.taskRunMeta,
.taskSubtitle,
.taskNodeMeta,
.taskNodeInfo {
  margin-top: 8px;
  font-size: 12px;
  color: rgba(31, 35, 41, 0.56);
}
.taskEmpty {
  padding: 16px 4px;
  font-size: 13px;
  color: rgba(31, 35, 41, 0.58);
}
.taskEmptyMain {
  margin: auto;
}
.taskMain {
  display: flex;
  flex-direction: column;
  padding: 14px;
  overflow: auto;
}
.taskHeader {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.taskStats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  min-width: 320px;
}
.taskStat {
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(31, 35, 41, 0.04);
  border: 1px solid rgba(31, 35, 41, 0.06);
}
.taskStat span {
  display: block;
  font-size: 12px;
  color: rgba(31, 35, 41, 0.58);
}
.taskStat strong {
  display: block;
  margin-top: 4px;
  font-size: 18px;
}
.taskGoalCard,
.taskSection {
  margin-top: 12px;
  border: 1px solid rgba(31, 35, 41, 0.06);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.86);
  padding: 14px;
}
.taskGoalText {
  margin-top: 10px;
  font-size: 13px;
  line-height: 1.6;
  color: rgba(31, 35, 41, 0.78);
  white-space: pre-wrap;
}
.taskSectionHeader {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.taskSectionTitle {
  font-weight: 900;
  font-size: 14px;
}
.taskLoading {
  padding: 18px 0 8px;
  font-size: 13px;
  color: rgba(31, 35, 41, 0.58);
}
.taskNodeList {
  display: grid;
  gap: 10px;
  margin-top: 12px;
}
.taskNodeCard {
  border: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 14px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.94);
}
.taskNodeCard.statusPending {
  background: rgba(250, 250, 250, 0.92);
}
.taskNodeCard.statusRun {
  border-color: rgba(82, 183, 255, 0.24);
  background: rgba(82, 183, 255, 0.06);
}
.taskNodeCard.statusDone {
  border-color: rgba(49, 175, 111, 0.24);
  background: rgba(49, 175, 111, 0.06);
}
.taskNodeCard.statusBlocked {
  border-color: rgba(217, 45, 32, 0.24);
  background: rgba(217, 45, 32, 0.06);
}
.taskNodeTop {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.taskNodeTitle {
  font-size: 15px;
  font-weight: 900;
}
.taskNodeDetail {
  margin-top: 10px;
  font-size: 13px;
  line-height: 1.6;
  color: rgba(31, 35, 41, 0.78);
  white-space: pre-wrap;
}
.taskNodeInfo {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 14px;
}
.taskNodeActions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.drawerSection {
  border: 1px solid rgba(31, 35, 41, 0.06);
  border-radius: 14px;
  padding: 12px;
  margin-bottom: 12px;
  background: rgba(255, 255, 255, 0.7);
}
.secTitle {
  font-weight: 900;
  margin-bottom: 10px;
}
.kvRow {
  display: grid;
  grid-template-columns: 72px 1fr;
  gap: 10px;
  font-size: 12px;
  margin-bottom: 6px;
}
.kvRow .k {
  opacity: 0.6;
  font-weight: 800;
}
.kvRow .v {
  opacity: 0.9;
  word-break: break-all;
}
.memberList {
  display: grid;
  gap: 8px;
}
.eventList {
  margin-top: 6px;
  max-height: 180px;
  overflow: auto;
  display: grid;
  gap: 6px;
}
.eventRow {
  border: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 10px;
  padding: 8px 10px;
  background: rgba(255, 255, 255, 0.85);
}
.dagCanvasWrap {
  position: relative;
  margin-top: 8px;
  border: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 12px;
  background: rgba(249, 251, 255, 0.9);
  overflow: auto;
  min-height: 140px;
  max-height: 360px;
  min-width: 0;
}
.dagCanvasInnerTransform {
  position: relative;
  transform-origin: 0 0;
}
.dagCanvasInner {
  position: relative;
  transform-origin: 0 0;
}
.dagCanvasBig {
  min-height: 520px;
  max-height: calc(100vh - 180px);
}
.dagSvg {
  position: absolute;
  inset: 0;
  display: block;
  min-width: 0;
}
.dagNode {
  position: absolute;
  width: 220px;
  min-height: 108px;
  border-radius: 10px;
  padding: 8px;
  border: 1px solid rgba(31, 35, 41, 0.12);
  background: #fff;
  box-shadow: 0 4px 10px rgba(31, 35, 41, 0.06);
}
.dagNodeBig {
  border-width: 1.5px;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease, opacity 0.15s ease;
}
.dagNodeBig:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(31, 35, 41, 0.1);
}
.dagNodeActive {
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.35), 0 10px 22px rgba(37, 99, 235, 0.15);
  border-color: rgba(37, 99, 235, 0.55);
}
.dagNodeDim {
  opacity: 0.35;
}
.dagNodeKey {
  font-size: 11px;
  font-weight: 900;
  color: #2f6bff;
}
.dagNodeTitle {
  margin-top: 2px;
  font-size: 13px;
  font-weight: 900;
}
.dagNodeMeta {
  margin-top: 6px;
  font-size: 11px;
  opacity: 0.68;
}
.graphLegend {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
.graphToolbar {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 10px;
}
.graphShell {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 12px;
}
.graphNodeList {
  border: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 10px;
  background: #fff;
  max-height: calc(100vh - 240px);
  overflow: auto;
  padding: 8px;
}
.graphNodeItem {
  border: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 8px;
  padding: 8px;
  cursor: pointer;
  margin-bottom: 8px;
}
.graphNodeItem:hover {
  background: rgba(79, 140, 255, 0.06);
}
.graphNodeItem.active {
  border-color: rgba(37, 99, 235, 0.45);
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.12);
  background: rgba(79, 140, 255, 0.08);
}
.graphNodeItemTitle {
  font-size: 12px;
  font-weight: 900;
}
.graphNodeItemMeta {
  margin-top: 2px;
  font-size: 11px;
  opacity: 0.7;
}
.graphMain {
  min-width: 0;
}
.graphEdgeTip {
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 800;
  color: #1d4ed8;
}
.graphEdge {
  cursor: pointer;
}
.graphEdge.active {
  filter: drop-shadow(0 0 3px rgba(37, 99, 235, 0.45));
}
.legendItem {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  border: 1px solid rgba(31, 35, 41, 0.1);
}
.eventHead {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
  cursor: pointer;
}
.eType {
  font-size: 12px;
  font-weight: 800;
}
.eTime {
  margin-top: 2px;
  font-size: 11px;
  opacity: 0.6;
}
.payloadBox {
  margin: 8px 0 0 0;
  padding: 8px;
  border-radius: 8px;
  border: 1px solid rgba(31, 35, 41, 0.08);
  background: rgba(31, 35, 41, 0.03);
  font-size: 11px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}
.depsEditor {
  display: grid;
  gap: 10px;
  max-height: 420px;
  overflow: auto;
  padding-right: 2px;
}
.depsRow {
  display: grid;
  grid-template-columns: 220px 46px 1fr;
  gap: 8px;
  align-items: center;
}
.depsNode {
  border: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 10px;
  padding: 8px 10px;
  background: rgba(255, 255, 255, 0.85);
}
.depsKey {
  font-size: 11px;
  font-weight: 900;
  color: #2f6bff;
}
.depsTitle {
  margin-top: 2px;
  font-size: 12px;
  font-weight: 700;
}
.depsArrow {
  text-align: center;
  font-size: 12px;
  opacity: 0.65;
}
.memberRow {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border: 1px solid rgba(31, 35, 41, 0.06);
  border-radius: 12px;
  padding: 10px;
}
.memberRow.statusPending {
  background: rgba(250, 250, 250, 0.8);
}
.memberRow.statusRun {
  background: rgba(82, 183, 255, 0.08);
  border-color: rgba(82, 183, 255, 0.24);
}
.memberRow.statusDone {
  background: rgba(49, 175, 111, 0.08);
  border-color: rgba(49, 175, 111, 0.24);
}
.memberRow.statusBlocked {
  background: rgba(217, 45, 32, 0.08);
  border-color: rgba(217, 45, 32, 0.24);
}
.mName {
  font-weight: 900;
}
.mMeta {
  font-size: 12px;
  opacity: 0.6;
  margin-top: 2px;
}
.blockTip {
  margin-top: 5px;
  font-size: 12px;
  color: #b42318;
}
.addGrid {
  display: grid;
  grid-template-columns: 120px 1fr 90px;
  gap: 10px;
  align-items: center;
}

.chatHeader {
  height: 58px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 18px;
  border-bottom: 1px solid rgba(31, 35, 41, 0.06);
}
.chatTitle {
  font-size: 16px;
  font-weight: 900;
}
.chatActions {
  display: flex;
  gap: 8px;
  align-items: center;
}
.iconBtn {
  border: 0;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: rgba(31, 35, 41, 0.06);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}
.iconBtnLarge {
  font-size: 17px;
}
.iconBtn:hover {
  background: rgba(31, 35, 41, 0.1);
}
.iconBtn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.chatBody {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 18px 18px 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.empty {
  margin: auto;
  opacity: 0.6;
}
.timeLine {
  align-self: center;
  font-size: 12px;
  opacity: 0.55;
  margin: 8px 0;
}
.msgRow {
  display: flex;
}
.msgRow.left {
  justify-content: flex-start;
}
.msgRow.right {
  justify-content: flex-end;
}
.bubble {
  max-width: 72%;
  padding: 10px 12px;
  border-radius: 14px;
  background: #fff;
  border: 1px solid rgba(31, 35, 41, 0.06);
  line-height: 1.5;
}
.msgRow.right .bubble {
  background: rgba(79, 140, 255, 0.14);
  border-color: rgba(79, 140, 255, 0.18);
}
.msgMeta {
  font-size: 12px;
  opacity: 0.6;
  margin-bottom: 4px;
}
.msgText {
  white-space: pre-wrap;
}

.chatComposer {
  margin: 0 18px 18px;
  min-height: 160px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 22px;
  box-shadow: 0 10px 28px rgba(31, 35, 41, 0.08);
}
.composerMid {
  position: relative;
  min-width: 0;
  width: 100%;
  display: flex;
  flex: 1;
}
.composerActions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  margin-top: auto;
}
.toolBtn {
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: 999px;
  background: rgba(31, 35, 41, 0.05);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}
.input {
  resize: none;
  width: 100%;
  min-height: 92px;
  border: 0;
  border-radius: 16px;
  padding: 10px 2px 10px 2px;
  outline: none;
  background: transparent;
  font-size: 14px;
  line-height: 1.6;
  box-sizing: border-box;
  align-self: stretch;
}
.mentionChips {
  position: absolute;
  top: -38px;
  left: 0;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(79, 140, 255, 0.12);
  border: 1px solid rgba(79, 140, 255, 0.18);
  font-size: 12px;
  font-weight: 800;
}
.chipX {
  border: 0;
  background: transparent;
  cursor: pointer;
  opacity: 0.7;
  font-weight: 900;
}
.chipX:hover {
  opacity: 1;
}
.mentionSuggest {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 64px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(31, 35, 41, 0.12);
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 14px 40px rgba(31, 35, 41, 0.12);
}
.msTitle {
  padding: 10px 12px;
  font-weight: 900;
  border-bottom: 1px solid rgba(31, 35, 41, 0.06);
}
.msList {
  max-height: 220px;
  overflow: auto;
}
.msItem {
  display: grid;
  grid-template-columns: 34px 1fr;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  cursor: pointer;
}
.msItem:hover {
  background: rgba(79, 140, 255, 0.06);
}
.msAvatar {
  width: 34px;
  height: 34px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  background: rgba(79, 140, 255, 0.14);
  font-size: 16px;
}
.msName {
  font-weight: 900;
}
.msEmpty {
  padding: 12px;
  opacity: 0.65;
  font-size: 12px;
}
.sendBtn {
  width: 46px;
  height: 46px;
  border: 0;
  border-radius: 50%;
  background: rgba(145, 145, 145, 0.92);
  color: #fff;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}
.sendBtn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.mentionList {
  display: grid;
  gap: 8px;
}
.mentionItem {
  display: grid;
  grid-template-columns: 36px 1fr 20px;
  align-items: center;
  gap: 10px;
  padding: 10px 10px;
  border-radius: 12px;
  cursor: pointer;
}
.mentionItem:hover {
  background: rgba(79, 140, 255, 0.06);
}
.mAvatar {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  background: rgba(79, 140, 255, 0.14);
  font-size: 16px;
}
.mName {
  font-weight: 800;
}
.mCheck {
  color: #2f6bff;
  display: flex;
  justify-content: center;
  font-size: 16px;
}

.createGrid {
  display: grid;
  grid-template-columns: 160px 1fr;
  gap: 10px;
}
.pickGrid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 10px;
}
.pickCol {
  border: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 14px;
  overflow: hidden;
}
.pickTitle {
  padding: 10px 12px;
  font-weight: 900;
  border-bottom: 1px solid rgba(31, 35, 41, 0.06);
}
.pickList {
  max-height: 280px;
  overflow: auto;
}
.pickItem {
  display: grid;
  grid-template-columns: 36px 1fr 20px;
  align-items: center;
  gap: 10px;
  padding: 10px 10px;
  cursor: pointer;
}
.pickItem:hover {
  background: rgba(79, 140, 255, 0.06);
}
.pAvatar {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  background: rgba(31, 35, 41, 0.06);
  font-size: 16px;
}
.pName {
  font-weight: 800;
}
.pCheck {
  color: #2f6bff;
  display: flex;
  justify-content: center;
  font-size: 16px;
}
.err {
  color: #d92d20;
  font-size: 12px;
}
</style>
