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

            <div class="panelCard taskSectionCard taskGraphCard">
              <div class="taskSectionHeader">
                <div>
                  <div class="taskSectionTitle">流程图</div>
                  <div class="taskSectionCaption">{{ graphCaption }}</div>
                </div>
                <div class="taskLegend">
                  <span class="taskLegendItem"><i class="legendDot statusPending"></i>待处理</span>
                  <span class="taskLegendItem"><i class="legendDot statusRun"></i>进行中</span>
                  <span class="taskLegendItem"><i class="legendDot statusDone"></i>已完成</span>
                  <span class="taskLegendItem"><i class="legendDot statusBlocked"></i>已阻塞</span>
                </div>
              </div>

              <div v-if="nodesLoading" class="taskLoading">加载流程图中…</div>
              <div v-else-if="graphLayout.nodes.length === 0" class="taskEmpty">当前 Run 还没有可展示的流程图</div>
              <div v-else class="taskGraphViewport">
                <div class="taskGraphCanvas" :style="graphCanvasStyle">
                  <svg class="taskGraphEdgeLayer" :viewBox="`0 0 ${graphLayout.width} ${graphLayout.height}`" preserveAspectRatio="none">
                    <defs>
                      <linearGradient id="taskGraphEdgeGradient" x1="0%" x2="100%" y1="0%" y2="0%">
                        <stop offset="0%" stop-color="rgba(13, 42, 79, 0.16)" />
                        <stop offset="100%" stop-color="rgba(79, 140, 255, 0.52)" />
                      </linearGradient>
                      <marker
                        id="taskGraphArrow"
                        markerWidth="10"
                        markerHeight="10"
                        refX="7"
                        refY="3"
                        orient="auto"
                        markerUnits="strokeWidth"
                      >
                        <path d="M0,0 L0,6 L7,3 z" fill="rgba(79, 140, 255, 0.8)" />
                      </marker>
                    </defs>
                    <path
                      v-for="edge in graphLayout.edges"
                      :key="edge.id"
                      class="taskGraphEdge"
                      :d="edge.path"
                      marker-end="url(#taskGraphArrow)"
                    />
                  </svg>

                  <div
                    v-for="column in graphLayout.columns"
                    :key="`column-${column.level}`"
                    class="taskGraphColumnLabel"
                    :style="{ left: `${column.x}px` }"
                  >
                    阶段 {{ column.level + 1 }}
                  </div>

                  <article
                    v-for="item in graphLayout.nodes"
                    :key="item.node.id"
                    class="taskGraphNode"
                    :class="nodeStatusClass(item.node.status)"
                    :style="{ left: `${item.x}px`, top: `${item.y}px` }"
                  >
                    <div class="taskGraphNodeTop">
                      <span class="taskGraphNodeKey">{{ item.node.node_key }}</span>
                      <span class="taskGraphNodeBadge">{{ taskStatusLabel(item.node.status) }}</span>
                    </div>
                    <div class="taskGraphNodeTitle">{{ item.node.title }}</div>
                    <div class="taskGraphNodeRole">{{ item.node.role_required || '未指定角色' }}</div>
                    <div class="taskGraphNodeDetail">{{ item.node.detail || '暂无说明' }}</div>
                    <div class="taskGraphNodeMeta">
                      <span>{{ item.node.deps?.length ? `依赖 ${item.node.deps.length} 项` : '起始节点' }}</span>
                      <span>{{ item.node.assignee_member_id ? senderName(item.node.assignee_member_id) : '待认领' }}</span>
                    </div>
                  </article>
                </div>
              </div>
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
                    <span>复核：{{ reviewStatusLabel(node.manager_review_status) }}</span>
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
import { computed } from 'vue'
import { Close } from '@element-plus/icons-vue'
import type { Group, GroupTaskNode, Member } from '../../api/groups'
import type { GroupTaskGraph, GroupTaskRun } from '../../api/messages'

const GRAPH_PADDING_X = 28
const GRAPH_PADDING_TOP = 56
const GRAPH_PADDING_BOTTOM = 24
const GRAPH_NODE_WIDTH = 220
const GRAPH_NODE_HEIGHT = 144
const GRAPH_COLUMN_GAP = 68
const GRAPH_ROW_GAP = 26

type GraphEdge = {
  from: string
  to: string
}

type GraphLayoutNode = {
  node: GroupTaskNode
  x: number
  y: number
}

type GraphLayoutEdge = {
  id: string
  path: string
}

type GraphLayoutColumn = {
  level: number
  x: number
  nodes: GroupTaskNode[]
}

const props = defineProps<{
  activeGroup: Group | null
  members: Member[]
  runs: GroupTaskRun[]
  activeRunId: string
  activeRun: GroupTaskRun | null
  graph: GroupTaskGraph | null
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

const graphNodes = computed<GroupTaskNode[]>(() => {
  if (props.graph?.nodes?.length) return props.graph.nodes as GroupTaskNode[]
  return props.nodes
})

const graphEdges = computed<GraphEdge[]>(() => {
  if (props.graph?.edges?.length) {
    const rawEdges = props.graph.edges as Array<{
      from?: string
      to?: string
      source?: string
      target?: string
    }>

    return rawEdges
      .map((edge, index) => ({
        from: String(edge.from ?? edge.source ?? `edge-from-${index}`),
        to: String(edge.to ?? edge.target ?? `edge-to-${index}`),
      }))
      .filter((edge) => edge.from && edge.to)
  }

  return graphNodes.value.flatMap((node) =>
    (node.deps || []).map((dep) => ({
      from: String(dep),
      to: String(node.node_key),
    })),
  )
})

const graphNodeMap = computed(() => new Map(graphNodes.value.map((node) => [String(node.node_key), node])))

const graphLevels = computed(() => {
  const memo = new Map<string, number>()
  const visiting = new Set<string>()

  function resolveLevel(nodeKey: string): number {
    if (memo.has(nodeKey)) return memo.get(nodeKey) || 0
    if (visiting.has(nodeKey)) return 0

    visiting.add(nodeKey)
    const node = graphNodeMap.value.get(nodeKey)
    const depLevels = (node?.deps || [])
      .map((dep) => graphNodeMap.value.has(String(dep)) ? resolveLevel(String(dep)) : 0)
      .filter((level) => Number.isFinite(level))
    const nextLevel = depLevels.length > 0 ? Math.max(...depLevels) + 1 : 0
    memo.set(nodeKey, nextLevel)
    visiting.delete(nodeKey)
    return nextLevel
  }

  for (const node of graphNodes.value) {
    resolveLevel(String(node.node_key))
  }

  const buckets = new Map<number, GroupTaskNode[]>()
  for (const node of graphNodes.value) {
    const level = memo.get(String(node.node_key)) || 0
    const current = buckets.get(level) || []
    current.push(node)
    buckets.set(level, current)
  }

  return Array.from(buckets.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([level, nodes]) => ({
      level,
      nodes,
    }))
})

const graphCaption = computed(() => {
  if (graphNodes.value.length === 0) return '根据节点依赖自动排布'
  return `${graphLevels.value.length} 个阶段 · ${graphNodes.value.length} 个节点 · ${graphEdges.value.length} 条依赖`
})

const graphLayout = computed(() => {
  const columns: GraphLayoutColumn[] = graphLevels.value.map((column, index) => ({
    level: column.level,
    x: GRAPH_PADDING_X + index * (GRAPH_NODE_WIDTH + GRAPH_COLUMN_GAP),
    nodes: column.nodes,
  }))

  const maxRows = Math.max(1, ...columns.map((column) => column.nodes.length))
  const width =
    GRAPH_PADDING_X * 2 +
    columns.length * GRAPH_NODE_WIDTH +
    Math.max(0, columns.length - 1) * GRAPH_COLUMN_GAP
  const height =
    GRAPH_PADDING_TOP +
    GRAPH_PADDING_BOTTOM +
    maxRows * GRAPH_NODE_HEIGHT +
    Math.max(0, maxRows - 1) * GRAPH_ROW_GAP

  const nodes: GraphLayoutNode[] = []
  const rectMap = new Map<
    string,
    { left: number; right: number; centerY: number }
  >()

  for (const column of columns) {
    const columnHeight =
      column.nodes.length * GRAPH_NODE_HEIGHT + Math.max(0, column.nodes.length - 1) * GRAPH_ROW_GAP
    const startY = GRAPH_PADDING_TOP + Math.max(0, (height - GRAPH_PADDING_TOP - GRAPH_PADDING_BOTTOM - columnHeight) / 2)

    column.nodes.forEach((node, index) => {
      const x = column.x
      const y = startY + index * (GRAPH_NODE_HEIGHT + GRAPH_ROW_GAP)
      nodes.push({ node, x, y })
      rectMap.set(String(node.node_key), {
        left: x,
        right: x + GRAPH_NODE_WIDTH,
        centerY: y + GRAPH_NODE_HEIGHT / 2,
      })
    })
  }

  const edges: GraphLayoutEdge[] = graphEdges.value
    .map((edge, index) => {
      const from = rectMap.get(String(edge.from))
      const to = rectMap.get(String(edge.to))
      if (!from || !to) return null
      const midX = from.right + (to.left - from.right) / 2
      const path = [
        `M ${from.right} ${from.centerY}`,
        `C ${midX} ${from.centerY}, ${midX} ${to.centerY}, ${to.left} ${to.centerY}`,
      ].join(' ')
      return {
        id: `edge-${index}-${edge.from}-${edge.to}`,
        path,
      }
    })
    .filter((edge): edge is GraphLayoutEdge => Boolean(edge))

  return {
    width: Math.max(width, 320),
    height: Math.max(height, GRAPH_PADDING_TOP + GRAPH_PADDING_BOTTOM + GRAPH_NODE_HEIGHT),
    columns,
    nodes,
    edges,
  }
})

const graphCanvasStyle = computed(() => ({
  width: `${graphLayout.value.width}px`,
  height: `${graphLayout.value.height}px`,
}))

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

function reviewStatusLabel(status: string) {
  if (status === 'approved') return '已通过'
  if (status === 'rework') return '待返工'
  return '待复核'
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
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}
.taskSectionCaption {
  font-size: 12px;
  color: rgba(31, 35, 41, 0.56);
  line-height: 1.5;
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
.taskGraphCard {
  margin-top: 12px;
  background:
    radial-gradient(circle at top left, rgba(79, 140, 255, 0.12), transparent 34%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(246, 249, 255, 0.94));
}
.taskLegend {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px 12px;
  font-size: 12px;
  color: rgba(31, 35, 41, 0.62);
}
.taskLegendItem {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.legendDot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  display: inline-block;
  background: rgba(31, 35, 41, 0.2);
}
.legendDot.statusPending {
  background: rgba(31, 35, 41, 0.32);
}
.legendDot.statusRun {
  background: rgba(82, 183, 255, 0.9);
}
.legendDot.statusDone {
  background: rgba(49, 175, 111, 0.9);
}
.legendDot.statusBlocked {
  background: rgba(217, 45, 32, 0.9);
}
.taskGraphViewport {
  overflow-x: auto;
  overflow-y: hidden;
  padding-bottom: 4px;
}
.taskGraphCanvas {
  position: relative;
  min-width: 100%;
  border-radius: 18px;
  background:
    linear-gradient(90deg, rgba(79, 140, 255, 0.05) 1px, transparent 1px) 0 0 / 24px 24px,
    linear-gradient(rgba(79, 140, 255, 0.05) 1px, transparent 1px) 0 0 / 24px 24px,
    linear-gradient(180deg, rgba(240, 246, 255, 0.95), rgba(255, 255, 255, 0.9));
  border: 1px solid rgba(79, 140, 255, 0.12);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.75);
}
.taskGraphEdgeLayer {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: visible;
  pointer-events: none;
}
.taskGraphEdge {
  fill: none;
  stroke: url(#taskGraphEdgeGradient);
  stroke-width: 2.5;
  stroke-linecap: round;
}
.taskGraphColumnLabel {
  position: absolute;
  top: 18px;
  transform: translateX(-2px);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.06em;
  color: rgba(13, 42, 79, 0.55);
  text-transform: uppercase;
}
.taskGraphNode {
  position: absolute;
  width: 220px;
  min-height: 144px;
  padding: 12px;
  border: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow:
    0 18px 38px rgba(13, 42, 79, 0.08),
    0 2px 8px rgba(13, 42, 79, 0.06);
  backdrop-filter: blur(4px);
}
.taskGraphNode.statusRun {
  background: linear-gradient(180deg, rgba(239, 249, 255, 0.98), rgba(226, 245, 255, 0.96));
  border-color: rgba(82, 183, 255, 0.28);
}
.taskGraphNode.statusDone {
  background: linear-gradient(180deg, rgba(240, 252, 246, 0.98), rgba(228, 247, 237, 0.96));
  border-color: rgba(49, 175, 111, 0.28);
}
.taskGraphNode.statusBlocked {
  background: linear-gradient(180deg, rgba(255, 243, 241, 0.98), rgba(252, 234, 231, 0.96));
  border-color: rgba(217, 45, 32, 0.3);
}
.taskGraphNodeTop {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.taskGraphNodeKey {
  font-size: 11px;
  font-weight: 800;
  color: rgba(13, 42, 79, 0.58);
  letter-spacing: 0.04em;
}
.taskGraphNodeBadge {
  white-space: nowrap;
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(13, 42, 79, 0.08);
  color: rgba(13, 42, 79, 0.72);
}
.taskGraphNodeTitle {
  margin-top: 10px;
  font-size: 15px;
  font-weight: 900;
  line-height: 1.35;
  color: #10233a;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.taskGraphNodeRole {
  margin-top: 6px;
  font-size: 12px;
  color: rgba(31, 35, 41, 0.56);
}
.taskGraphNodeDetail {
  margin-top: 10px;
  font-size: 12px;
  line-height: 1.55;
  color: rgba(31, 35, 41, 0.72);
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.taskGraphNodeMeta {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid rgba(31, 35, 41, 0.08);
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 11px;
  color: rgba(31, 35, 41, 0.6);
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
@media (max-width: 900px) {
  .taskSectionHeader {
    flex-direction: column;
  }
  .taskLegend {
    justify-content: flex-start;
  }
}
</style>
