<template>
  <div class="sidePanel">
    <div class="sideHeader">
      <div>
        <div class="sideTitle">部署</div>
        <div class="sideSubtitle">只保留预览和一键部署入口</div>
      </div>
      <el-button class="sideCloseBtn" :icon="Close" circle text @click="$emit('close')" aria-label="关闭部署面板" />
    </div>

    <div class="sideBody">
      <div v-if="supportsProjectWorkspace" class="deployShell">
        <div class="panelCard compactCard">
          <div class="cardTitleRow">
            <div class="sectionTitle">当前预览</div>
            <span class="statusPill" :data-status="previewTone">{{ previewLabel }}</span>
          </div>
          <div class="toolbar">
            <el-button
              v-if="previewJob"
              size="small"
              type="primary"
              :loading="previewPending"
              @click="$emit('open-preview')"
            >
              {{ previewJob.url ? '刷新' : '打开预览' }}
            </el-button>
            <el-button
              v-if="previewJob?.url"
              size="small"
              plain
              tag="a"
              :href="previewJob.url"
              target="_blank"
              rel="noreferrer"
            >
              预览地址
            </el-button>
            <el-button
              v-if="previewJob && previewJob.status !== 'stopped'"
              size="small"
              :disabled="previewPending"
              @click="$emit('close-preview')"
            >
              {{ previewPending ? '关闭中…' : '关闭预览' }}
            </el-button>
          </div>
          <div class="statusRow">
            <span class="statusLabel">地址</span>
            <a v-if="previewJob?.url" class="previewLink" :href="previewJob.url" target="_blank" rel="noreferrer">
              {{ previewJob.url }}
            </a>
            <span v-else class="statusValue">暂无预览</span>
          </div>
          <div v-if="previewJob?.error_message" class="errBox">{{ previewJob.error_message }}</div>
        </div>

        <div class="panelCard compactCard">
          <div class="cardTitleRow">
            <div>
              <div class="sectionTitle">一键部署</div>
              <div class="hint">参数已在编辑器里配置好，这里只负责执行。</div>
            </div>
            <span class="statusPill" :data-status="deploymentTone">{{ deploymentLabel }}</span>
          </div>
          <div class="toolbar">
            <el-button size="large" type="primary" :loading="deployPending" @click="$emit('deploy')">
              {{ deployPending ? '部署中…' : deploymentJob ? '重新部署' : '开始部署' }}
            </el-button>
            <el-button
              v-if="deploymentJob?.id && deploymentJob.status !== 'running' && deploymentJob.status !== 'pending'"
              size="small"
              :disabled="deployPending"
              @click="$emit('retry-deploy', deploymentJob.id)"
            >
              重试
            </el-button>
          </div>
          <div class="statusRow">
            <span class="statusLabel">部署地址</span>
            <a v-if="deploymentUrl" class="previewLink" :href="deploymentUrl" target="_blank" rel="noreferrer">
              {{ deploymentUrl }}
            </a>
            <span v-else class="statusValue">部署后生成</span>
          </div>
          <div v-if="deploymentJob?.error_message" class="errBox">{{ deploymentJob.error_message }}</div>
        </div>

        <details v-if="deploymentJob" class="advancedDetails">
          <summary>高级信息</summary>
          <div class="panelCard advancedCard">
            <div class="statusRow">
              <span class="statusLabel">镜像</span>
              <span class="mono">{{ deploymentJob.image_ref }}</span>
            </div>
            <div class="statusRow">
              <span class="statusLabel">容器</span>
              <span class="mono">{{ deploymentJob.container_name }}</span>
            </div>
            <div class="statusRow">
              <span class="statusLabel">容器 ID</span>
              <span class="mono">{{ shortContainerId }}</span>
            </div>
            <div class="statusRow">
              <span class="statusLabel">尝试次数</span>
              <span class="statusValue">{{ deploymentJob.attempt_count }}</span>
            </div>
            <details v-if="deploymentJob.logs_text" class="logDetails">
              <summary>查看日志</summary>
              <pre class="logBlock">{{ deploymentJob.logs_text }}</pre>
            </details>
          </div>
        </details>
      </div>

      <div v-else class="sideEmpty">
        <div class="empty">仅项目群聊支持部署</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Close } from '@element-plus/icons-vue'
import type { Group } from '../../api/groups'
import type { DeploymentJob } from '../../api/deployments'
import type { PreviewJob } from '../../api/previews'

const props = defineProps<{
  activeGroup: Group | null
  previewJob: PreviewJob | null
  previewPending: boolean
  deploymentJob: DeploymentJob | null
  deployPending: boolean
}>()

defineEmits<{
  (e: 'close'): void
  (e: 'close-preview'): void
  (e: 'open-preview'): void
  (e: 'deploy'): void
  (e: 'retry-deploy', deploymentId: number): void
}>()

const supportsProjectWorkspace = computed(() => {
  const group = props.activeGroup
  if (!group) return false
  return String(group.type || '') === 'project' || Number(group.workspace_id || 0) > 0
})

const deploymentTone = computed(() => {
  const status = props.deploymentJob?.status
  if (status === 'succeeded') return 'succeeded'
  if (status === 'failed') return 'failed'
  if (props.deployPending || status === 'running' || status === 'pending') return 'running'
  return 'idle'
})

const previewTone = computed(() => {
  const status = props.previewJob?.status || ''
  if (props.previewPending || status === 'running') return 'running'
  if (status === 'active') return 'succeeded'
  if (status === 'failed') return 'failed'
  return 'idle'
})

const deploymentLabel = computed(() => {
  if (props.deployPending || props.deploymentJob?.status === 'running') return '部署中'
  if (props.deploymentJob?.status === 'succeeded') return '已完成'
  if (props.deploymentJob?.status === 'failed') return '部署失败'
  return '未开始'
})

const previewLabel = computed(() => {
  const status = props.previewJob?.status || ''
  if (props.previewPending || status === 'running') return '刷新中'
  if (status === 'active') return '运行中'
  if (status === 'failed') return '预览失败'
  if (status === 'stopped') return '已关闭'
  return '未启动'
})

const deploymentUrl = computed(() => {
  const ports = Array.isArray(props.deploymentJob?.spec?.ports) ? props.deploymentJob?.spec?.ports : []
  const firstPort = ports[0]
  if (!firstPort || typeof firstPort !== 'object') return ''
  const hostPort = Number((firstPort as { host_port?: unknown }).host_port)
  return Number.isFinite(hostPort) && hostPort > 0 ? `http://127.0.0.1:${hostPort}` : ''
})

const shortContainerId = computed(() => {
  const containerId = props.deploymentJob?.deployed_container_id || ''
  return containerId ? containerId.slice(0, 12) : '尚未生成'
})
</script>

<style scoped>
.sidePanel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--ah-panel-bg);
  backdrop-filter: blur(10px);
  border: 1px solid var(--ah-panel-border, var(--ah-border));
  border-radius: 18px;
  overflow: hidden;
  min-width: 0;
}
.sideHeader {
  height: 56px;
  padding: 0 16px;
  border-bottom: 1px solid var(--ah-border-soft);
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
  color: var(--ah-text-tertiary);
}
.sideCloseBtn {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  color: var(--ah-text-secondary);
  background: var(--ah-surface-soft);
}

.sideCloseBtn:hover {
  background: var(--ah-surface);
}
.sideBody {
  flex: 1;
  min-height: 0;
  padding: 12px;
}
.deployShell {
  display: grid;
  gap: 12px;
}
.panelCard {
  border: 1px solid var(--ah-border-soft);
  border-radius: 16px;
  background: var(--ah-surface-soft);
  padding: 14px;
  display: grid;
  gap: 12px;
}
.compactCard {
  gap: 10px;
}
.sectionTitle {
  font-size: 14px;
  font-weight: 900;
}
.cardTitleRow {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.statusPill {
  flex: 0 0 auto;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--ah-surface);
  color: var(--ah-text-secondary);
  font-size: 12px;
  font-weight: 700;
}
.statusPill[data-status='succeeded'] {
  background: rgba(34, 197, 94, 0.12);
  color: #15803d;
}
.statusPill[data-status='failed'] {
  background: rgba(220, 38, 38, 0.12);
  color: #b91c1c;
}
.statusPill[data-status='running'] {
  background: rgba(59, 130, 246, 0.12);
  color: #2563eb;
}
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.statusRow {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  font-size: 13px;
}
.statusLabel {
  color: var(--ah-text-tertiary);
  flex: 0 0 auto;
}
.statusValue {
  color: var(--ah-text-primary);
  text-align: right;
  min-width: 0;
}
.previewLink {
  color: var(--ah-primary-strong);
  text-decoration: none;
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.previewLink:hover {
  text-decoration: underline;
}
.errBox {
  border-radius: 12px;
  border: 1px solid rgba(220, 38, 38, 0.22);
  background: rgba(220, 38, 38, 0.08);
  color: var(--ah-danger);
  font-size: 12px;
  padding: 10px 12px;
  line-height: 1.5;
  white-space: pre-wrap;
}
.hint {
  color: var(--ah-text-tertiary);
  font-size: 12px;
  line-height: 1.5;
}
.advancedDetails {
  border-top: 1px dashed var(--ah-border);
  padding-top: 2px;
}
.advancedDetails > summary {
  cursor: pointer;
  color: var(--ah-text-secondary);
  font-weight: 700;
  padding: 8px 2px 4px;
}
.advancedCard {
  margin-top: 10px;
}
.logDetails {
  border-top: 1px dashed var(--ah-border);
  padding-top: 10px;
}
.logDetails summary {
  cursor: pointer;
  color: var(--ah-text-secondary);
  font-weight: 700;
}
.logBlock {
  margin: 10px 0 0;
  padding: 12px;
  border-radius: 12px;
  background: var(--ah-code-bg);
  color: var(--ah-text-primary);
  overflow: auto;
  max-height: 240px;
  white-space: pre-wrap;
  word-break: break-word;
}
.mono {
  font-family:
    ui-monospace,
    SFMono-Regular,
    SF Mono,
    Consolas,
    Liberation Mono,
    Menlo,
    monospace;
  font-size: 12px;
  color: var(--ah-text-secondary);
}
.sideEmpty {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.empty {
  color: var(--ah-text-tertiary);
}
</style>
