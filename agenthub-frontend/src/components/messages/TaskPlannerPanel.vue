<template>
  <div class="sidePanel">
    <div class="sideHeader">
      <div>
        <div class="sideTitle">任务规划</div>
        <div class="sideSubtitle">{{ activeGroup?.name || '未选择会话' }}</div>
      </div>
      <el-button class="sideCloseBtn" :icon="Close" circle text @click="$emit('close')" aria-label="关闭任务规划" />
    </div>

    <el-scrollbar class="sideBody">
      <template v-if="activeGroup?.type === 'project'">
        <div class="plannerHero">
          <div>
            <div class="plannerLabel">项目任务图</div>
            <div class="plannerHeadline">当前项目直接维护一套任务节点，不区分 Run。</div>
          </div>
          <div class="plannerHeroActions">
            <el-button type="primary" @click="$emit('create-nodes')">新增节点</el-button>
            <el-button :loading="nodesLoading" @click="$emit('refresh-nodes')">刷新</el-button>
          </div>
        </div>

        <div class="heroCard">
          <div class="heroTop">
            <div>
              <div class="heroTitle">项目任务概览</div>
              <div class="heroSubtitle">节点直接归属于当前项目群，可认领、完成和继续拆分。</div>
            </div>
          </div>

          <div class="statsGrid">
            <div class="statCard">
              <span>总节点</span>
              <strong>{{ nodeStats.total }}</strong>
            </div>
            <div class="statCard">
              <span>进行中</span>
              <strong>{{ nodeStats.running }}</strong>
            </div>
            <div class="statCard">
              <span>已完成</span>
              <strong>{{ nodeStats.completed }}</strong>
            </div>
            <div class="statCard">
              <span>已阻塞</span>
              <strong>{{ nodeStats.blocked }}</strong>
            </div>
          </div>
        </div>

        <div class="nodesCard">
          <div class="nodesHeader">
            <div>
              <div class="sectionTitle">节点列表</div>
              <div class="sectionHint">按状态推进节点，成员认领后完成并提交结果摘要。</div>
            </div>
          </div>

          <div v-if="nodesLoading" class="taskEmpty">加载节点中…</div>
          <div v-else-if="nodes.length === 0" class="taskEmpty">当前项目还没有任务节点，先创建一个。</div>
          <div v-else class="nodeList">
            <article v-for="row in nodes" :key="String(row.id)" class="nodeCard">
              <div class="nodeCardTop">
                <div class="nodeMain">
                  <div class="nodeTitleRow">
                    <div class="nodeTitle">{{ row.title }}</div>
                    <span class="nodeStatus" :class="statusClass(row.status)">
                      {{ taskStatusLabel(row.status) }}
                    </span>
                  </div>
                  <div class="nodeMeta">
                    {{ row.node_key }} · {{ row.role_required || '未指定角色' }} ·
                    {{ row.assignee_member_id ? senderName(row.assignee_member_id) : '待认领' }}
                  </div>
                </div>
              </div>

              <div class="nodeDetail">{{ row.detail || '暂无说明' }}</div>

              <div class="nodeFoot">
                <div class="depsLine">
                  <span class="depsLabel">依赖</span>
                  <span class="depsValue">{{ (row.deps || []).join(', ') || '无' }}</span>
                </div>
                <div class="taskNodeActions">
                  <el-button size="small" v-if="row.status === 'pending'" @click="$emit('claim-node', row)">认领</el-button>
                  <el-button
                    size="small"
                    type="primary"
                    v-if="row.status === 'running' && isNodeMine(row)"
                    @click="$emit('complete-node', row)"
                  >
                    完成
                  </el-button>
                </div>
              </div>
            </article>
          </div>
        </div>
      </template>

      <div v-else class="emptyState">
        <div class="emptyTitle">仅项目群聊支持任务规划</div>
        <div class="emptyText">把多人协作过程拆成节点、认领和完成。</div>
      </div>

      <div v-if="manageErr" class="panelError">{{ manageErr }}</div>
    </el-scrollbar>
  </div>
</template>

<script setup lang="ts">
import { Close } from '@element-plus/icons-vue'
import type { Group, GroupTaskNode, Member } from '@/api/models.ts'

const props = defineProps<{
  activeGroup: Group | null
  members: Member[]
  nodes: GroupTaskNode[]
  nodeStats: { total: number; running: number; completed: number; blocked: number }
  nodesLoading: boolean
  manageErr: string
}>()

defineEmits<{
  (e: 'close'): void
  (e: 'refresh-nodes'): void
  (e: 'create-nodes'): void
  (e: 'claim-node', node: GroupTaskNode): void
  (e: 'complete-node', node: GroupTaskNode): void
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

function statusClass(status: string) {
  if (status === 'completed') return 'success'
  if (status === 'running') return 'primary'
  if (status === 'blocked') return 'danger'
  return 'info'
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
  background: var(--ah-surface);
  backdrop-filter: blur(10px);
  border: 1px solid var(--ah-border);
  border-radius: 26px;
  overflow: hidden;
  min-width: 0;
  box-shadow: var(--ah-shadow-md);
}
.sideHeader {
  min-height: 74px;
  padding: 14px 20px;
  border-bottom: 1px solid var(--ah-border-soft);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex: 0 0 auto;
}
.sideTitle {
  font-size: 18px;
  font-weight: 900;
}
.sideSubtitle {
  margin-top: 4px;
  font-size: 12px;
  color: var(--ah-text-tertiary);
}
.sideCloseBtn {
  width: 40px;
  height: 40px;
  border-radius: 14px;
  color: var(--ah-text-secondary);
  background: var(--ah-surface-soft);
}
.sideBody {
  flex: 1;
  min-height: 0;
  padding: 20px 20px 24px;
}
.plannerHero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 4px 2px 20px;
}
.plannerLabel {
  font-size: 12px;
  font-weight: 800;
  color: var(--ah-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.plannerHeadline {
  margin-top: 6px;
  font-size: 20px;
  line-height: 1.35;
  font-weight: 900;
  color: var(--ah-text-primary);
  max-width: 560px;
}
.plannerHeroActions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.heroCard,
.nodesCard,
.emptyState {
  border: 1px solid var(--ah-border-soft);
  border-radius: 24px;
  background: var(--ah-surface-soft);
}
.heroCard,
.nodesCard {
  padding: 18px;
}
.nodesCard {
  margin-top: 14px;
}
.heroTitle,
.sectionTitle {
  font-size: 14px;
  font-weight: 900;
  color: var(--ah-text-primary);
}
.heroSubtitle,
.sectionHint,
.emptyText {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--ah-text-tertiary);
}
.statsGrid {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}
.statCard {
  border-radius: 18px;
  background: var(--ah-surface);
  border: 1px solid var(--ah-border-soft);
  padding: 12px;
  display: grid;
  gap: 6px;
}
.statCard span {
  font-size: 12px;
  color: var(--ah-text-tertiary);
}
.statCard strong {
  font-size: 24px;
  color: var(--ah-text-primary);
}
.nodeList {
  margin-top: 14px;
  display: grid;
  gap: 12px;
}
.nodeCard {
  border: 1px solid var(--ah-border-soft);
  border-radius: 22px;
  background: var(--ah-surface);
  padding: 16px;
}
.nodeCardTop {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.nodeMain {
  min-width: 0;
}
.nodeTitleRow {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  flex-wrap: wrap;
}
.nodeTitle {
  font-size: 15px;
  font-weight: 900;
  color: var(--ah-text-primary);
}
.nodeStatus {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
  white-space: nowrap;
}
.nodeStatus.info {
  background: var(--ah-surface);
  color: var(--ah-text-secondary);
  border: 1px solid var(--ah-border-soft);
}
.nodeStatus.primary {
  background: var(--ah-primary-ghost);
  color: var(--ah-primary-strong);
}
.nodeStatus.success {
  background: rgba(51, 194, 107, 0.14);
  color: var(--ah-success);
}
.nodeStatus.danger {
  background: rgba(239, 68, 68, 0.12);
  color: var(--ah-danger);
}
.nodeMeta {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--ah-text-tertiary);
}
.nodeDetail {
  margin-top: 12px;
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
  color: var(--ah-text-secondary);
}
.nodeFoot {
  margin-top: 14px;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.depsLine {
  display: grid;
  gap: 4px;
}
.depsLabel {
  font-size: 12px;
  font-weight: 800;
  color: var(--ah-text-tertiary);
}
.depsValue {
  font-size: 13px;
  color: var(--ah-text-secondary);
}
.taskNodeActions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.taskEmpty,
.emptyTitle {
  font-size: 14px;
  font-weight: 800;
  color: var(--ah-text-primary);
}
.taskEmpty {
  padding: 18px 4px;
}
.emptyState {
  padding: 24px;
  display: grid;
  gap: 10px;
  justify-items: start;
}
.panelError {
  margin-top: 14px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--ah-danger);
}
</style>
