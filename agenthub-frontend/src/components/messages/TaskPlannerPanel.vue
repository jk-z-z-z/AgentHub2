<template>
  <div class="sidePanel">
    <div class="sideHeader">
      <div>
        <div class="sideTitle">任务规划</div>
        <div class="sideSubtitle">{{ activeGroup?.name || '未选择会话' }}</div>
      </div>
      <button class="sideCloseBtn" type="button" aria-label="关闭任务规划" @click="$emit('close')">
        <el-icon>
          <Close />
        </el-icon>
      </button>
    </div>

    <div class="sideBody">
      <div v-if="activeGroup?.type === 'project'" class="taskShell">
        <section class="taskSidebar">
          <div class="panelCard">
            <div class="taskToolbar">
              <el-button size="small" type="primary" @click="$emit('create-run')">新建 Run</el-button>
              <el-button size="small" @click="$emit('refresh-runs')" :loading="runsLoading">刷新</el-button>
            </div>
            <div class="taskHint">只保留常用操作：创建 Run、查看节点状态、认领、完成、复核。</div>
          </div>

          <div class="taskRunList">
            <button
              v-for="run in runs"
              :key="run.id"
              class="taskRunItem"
              :class="{ active: String(run.id) === String(activeRunId) }"
              @click="$emit('select-run', String(run.id))"
            >
              <div class="taskRunTop">
                <div class="taskRunTitle">{{ run.title }}</div>
                <div class="taskRunStatus">{{ run.status }}</div>
              </div>
              <div class="taskRunGoal">{{ run.goal_text }}</div>
              <div class="taskRunMeta">{{ new Date(run.created_at).toLocaleDateString() }} · Run #{{ run.id }}</div>
            </button>
            <div v-if="!runsLoading && runs.length === 0" class="taskEmpty">还没有 Run，先点“新建 Run”</div>
          </div>
        </section>

        <section class="taskMain">
          <template v-if="activeRun">
            <div class="panelCard taskHeaderCard">
              <div class="taskHeader">
                <div>
                  <div class="taskTitle">{{ activeRun.title }}</div>
                  <div class="taskSubtitle">
                    {{ activeRun.status }} · {{ activeRun.created_at ? new Date(activeRun.created_at).toLocaleString() : '-' }}
                  </div>
                </div>
                <div class="taskStats">
                  <div class="taskStat"><span>总节点</span><strong>{{ nodeStats.total }}</strong></div>
                  <div class="taskStat"><span>进行中</span><strong>{{ nodeStats.running }}</strong></div>
                  <div class="taskStat"><span>已完成</span><strong>{{ nodeStats.completed }}</strong></div>
                  <div class="taskStat"><span>已阻塞</span><strong>{{ nodeStats.blocked }}</strong></div>
                </div>
              </div>
            </div>

            <div class="panelCard">
              <div class="taskSectionTitle">任务目标</div>
              <div class="taskGoalText">{{ activeRun.goal_text }}</div>
            </div>

            <div class="panelCard taskSectionCard">
              <div class="taskSectionHeader">
                <div class="taskSectionTitle">节点列表</div>
                <el-button size="small" :loading="nodesLoading" @click="$emit('refresh-run-details', String(activeRunId))">刷新节点</el-button>
              </div>

              <div v-if="nodesLoading" class="taskLoading">加载节点中…</div>
              <div v-else class="taskNodeList">
                <div v-for="node in nodes" :key="node.id" class="taskNodeCard" :class="nodeStatusClass(node.status)">
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
                    <el-button size="small" v-if="node.status === 'pending'" @click="$emit('claim-node', node)">认领</el-button>
                    <el-button
                      size="small"
                      type="primary"
                      v-if="node.status === 'running' && isNodeMine(node)"
                      @click="$emit('complete-node', node)"
                    >
                      完成
                    </el-button>
                    <el-button
                      size="small"
                      v-if="node.status === 'completed' && node.manager_review_status === 'pending'"
                      @click="$emit('review-node', node, 'approved')"
                    >
                      复核通过
                    </el-button>
                    <el-button
                      size="small"
                      type="danger"
                      plain
                      v-if="node.status === 'completed' && node.manager_review_status === 'pending'"
                      @click="$emit('review-node', node, 'rework')"
                    >
                      要求返工
                    </el-button>
                  </div>
                </div>
                <div v-if="nodes.length === 0" class="taskEmpty">当前 Run 还没有节点</div>
              </div>
            </div>
          </template>

          <div v-else class="sideEmpty">
            <div class="empty">暂无可查看的任务 Run，请先新建一个。</div>
          </div>
        </section>
      </div>

      <div v-else class="sideEmpty">
        <div class="empty">仅项目群聊支持任务规划</div>
      </div>

      <div v-if="manageErr" class="panelError">{{ manageErr }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Close } from '@element-plus/icons-vue'
import type { Group, GroupTaskNode, Member } from '../../api/groups'
import type { GroupTaskRun } from '../../api/messages'

const props = defineProps<{
  activeGroup: Group | null
  members: Member[]
  runs: GroupTaskRun[]
  activeRunId: string
  activeRun: GroupTaskRun | null
  nodes: GroupTaskNode[]
  nodeStats: { total: number; running: number; completed: number; blocked: number }
  runsLoading: boolean
  nodesLoading: boolean
  manageErr: string
}>()

defineEmits<{
  (e: 'close'): void
  (e: 'refresh-runs'): void
  (e: 'select-run', runId: string): void
  (e: 'create-run'): void
  (e: 'refresh-run-details', runId: string): void
  (e: 'claim-node', node: GroupTaskNode): void
  (e: 'complete-node', node: GroupTaskNode): void
  (e: 'review-node', node: GroupTaskNode, status: 'approved' | 'rework'): void
}>()

function senderName(memberId: string) {
  const member = props.members.find((item) => String(item.id) === String(memberId))
  return member?.display_name || String(memberId)
}

function taskStatusLabel(status: string) {
  if (status === 'completed') return '已完成'
  if (status === 'running') return '进行中'
  if (status === 'blocked') return '已阻塞'
  return '待处理'
}

function nodeStatusClass(status: string) {
  if (status === 'completed') return 'statusDone'
  if (status === 'running') return 'statusRun'
  if (status === 'blocked') return 'statusBlocked'
  return 'statusPending'
}

function isNodeMine(node: GroupTaskNode) {
  const me = props.members.find((member) => member.kind === 'user')
  return !!me && String(node.assignee_member_id || '') === String(me.id)
}
</script>

<style scoped>
.sidePanel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.84);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 18px;
  overflow: hidden;
  min-width: 0;
}
.sideHeader {
  height: 58px;
  padding: 0 16px;
  border-bottom: 1px solid rgba(31, 35, 41, 0.06);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex: 0 0 auto;
}
.sideTitle {
  font-size: 16px;
  font-weight: 900;
}
.sideSubtitle {
  margin-top: 2px;
  font-size: 12px;
  color: rgba(31, 35, 41, 0.58);
}
.sideCloseBtn {
  border: 0;
  width: 32px;
  height: 32px;
  border-radius: 10px;
  background: rgba(31, 35, 41, 0.06);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: rgba(31, 35, 41, 0.8);
}
.sideCloseBtn:hover {
  background: rgba(31, 35, 41, 0.1);
}
.sideBody {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 12px;
}
.taskShell {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 12px;
  min-height: 0;
}
.taskSidebar,
.taskMain {
  min-width: 0;
  min-height: 0;
}
.panelCard {
  border: 1px solid rgba(31, 35, 41, 0.06);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.78);
  padding: 12px;
}
.taskToolbar {
  display: flex;
  gap: 8px;
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
  gap: 8px;
}
.taskRunItem {
  border: 1px solid rgba(31, 35, 41, 0.06);
  border-radius: 14px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.8);
  cursor: pointer;
  text-align: left;
}
.taskRunItem:hover {
  background: rgba(79, 140, 255, 0.06);
}
.taskRunItem.active {
  background: rgba(79, 140, 255, 0.12);
  border-color: rgba(79, 140, 255, 0.18);
}
.taskRunTop {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.taskRunTitle {
  font-weight: 900;
}
.taskRunStatus {
  font-size: 12px;
  opacity: 0.65;
  white-space: nowrap;
}
.taskRunGoal {
  margin-top: 6px;
  font-size: 13px;
  opacity: 0.75;
  line-height: 1.5;
}
.taskRunMeta {
  margin-top: 8px;
  font-size: 12px;
  opacity: 0.55;
}
.taskHeaderCard {
  margin-bottom: 12px;
}
.taskHeader {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.taskTitle {
  font-size: 18px;
  font-weight: 900;
}
.taskSubtitle {
  margin-top: 4px;
  font-size: 12px;
  opacity: 0.62;
}
.taskStats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}
.taskStat {
  border-radius: 12px;
  background: rgba(31, 35, 41, 0.04);
  padding: 10px 8px;
  display: grid;
  gap: 4px;
  text-align: center;
}
.taskStat span {
  font-size: 12px;
  opacity: 0.6;
}
.taskStat strong {
  font-size: 18px;
}
.taskSectionTitle {
  font-weight: 900;
  margin-bottom: 10px;
}
.taskGoalText {
  line-height: 1.7;
  white-space: pre-wrap;
}
.taskSectionCard {
  margin-top: 12px;
}
.taskSectionHeader {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}
.taskLoading,
.taskEmpty,
.empty {
  padding: 16px 4px;
  font-size: 13px;
  color: rgba(31, 35, 41, 0.58);
}
.taskNodeList {
  display: grid;
  gap: 10px;
}
.taskNodeCard {
  border: 1px solid rgba(31, 35, 41, 0.06);
  border-radius: 14px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.8);
}
.taskNodeCard.statusRun {
  background: rgba(82, 183, 255, 0.08);
  border-color: rgba(82, 183, 255, 0.24);
}
.taskNodeCard.statusDone {
  background: rgba(49, 175, 111, 0.08);
  border-color: rgba(49, 175, 111, 0.24);
}
.taskNodeCard.statusBlocked {
  background: rgba(217, 45, 32, 0.08);
  border-color: rgba(217, 45, 32, 0.24);
}
.taskNodeTop {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}
.taskNodeTitle {
  font-weight: 900;
}
.taskNodeMeta {
  margin-top: 3px;
  font-size: 12px;
  opacity: 0.58;
}
.taskNodeBadge {
  white-space: nowrap;
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(31, 35, 41, 0.06);
}
.taskNodeDetail {
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
}
.taskNodeInfo {
  margin-top: 10px;
  display: grid;
  gap: 4px;
  font-size: 12px;
  opacity: 0.68;
}
.taskNodeActions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}
.taskEmptyMain,
.sideEmpty {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.panelError {
  margin-top: 12px;
  color: #d92d20;
  font-size: 12px;
}
@media (max-width: 1200px) {
  .taskShell {
    grid-template-columns: 1fr;
  }
}
</style>
