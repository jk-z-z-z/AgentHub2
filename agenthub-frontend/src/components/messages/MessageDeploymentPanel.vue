<template>
  <div class="sidePanel">
    <div class="sideHeader">
      <div>
        <div class="sideTitle">部署</div>
        <div class="sideSubtitle">编辑器里设置参数，这里只负责一键执行</div>
      </div>
      <button class="sideCloseBtn" type="button" aria-label="关闭部署面板" @click="$emit('close')">
        <el-icon>
          <Close />
        </el-icon>
      </button>
    </div>

    <div class="sideBody">
      <div v-if="supportsProjectWorkspace" class="deployShell">
        <div class="panelCard heroCard">
          <div class="sectionTitle">当前预览</div>
          <div class="toolbar">
            <el-button
              v-if="previewJob"
              size="small"
              type="primary"
              :loading="previewPending"
              @click="$emit('open-preview')"
            >
              {{ previewJob.url ? '刷新预览' : '重新打开预览' }}
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
              打开预览
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
            <span class="statusLabel">状态</span>
            <span class="statusValue" :data-status="previewTone">{{ previewLabel }}</span>
          </div>
          <div class="statusRow">
            <span class="statusLabel">地址</span>
            <a v-if="previewJob?.url" class="previewLink" :href="previewJob.url" target="_blank" rel="noreferrer">
              {{ previewJob.url }}
            </a>
            <span v-else class="statusValue">暂无预览</span>
          </div>
          <div class="statusRow">
            <span class="statusLabel">最近刷新</span>
            <span class="statusValue">{{ previewUpdatedAt }}</span>
          </div>
          <div v-if="previewJob?.error_message" class="errBox">{{ previewJob.error_message }}</div>
        </div>

        <div class="panelCard deployCard">
          <div class="deployHeader">
            <div>
              <div class="sectionTitle">一键部署</div>
              <div class="hint">部署参数已放在编辑器页里，这里只要点击一次就可以。</div>
            </div>
            <el-tag size="small" type="info">简化模式</el-tag>
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
            <span class="statusLabel">状态</span>
            <span class="statusValue" :data-status="deploymentTone">{{ deploymentLabel }}</span>
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

        <div v-if="deploymentJob" class="panelCard">
          <div class="sectionTitle">最近一次部署</div>
          <div class="statusRow">
            <span class="statusLabel">镜像</span>
            <span class="mono">{{ deploymentJob.image_ref }}</span>
          </div>
          <div class="statusRow">
            <span class="statusLabel">容器</span>
            <span class="mono">{{ deploymentJob.container_name }}</span>
          </div>
          <div class="statusRow">
            <span class="statusLabel">尝试次数</span>
            <span class="statusValue">{{ deploymentJob.attempt_count }}</span>
          </div>
          <div class="statusRow">
            <span class="statusLabel">容器 ID</span>
            <span class="mono">{{ shortContainerId }}</span>
          </div>
          <details v-if="deploymentJob.logs_text" class="logDetails">
            <summary>查看日志</summary>
            <pre class="logBlock">{{ deploymentJob.logs_text }}</pre>
          </details>
        </div>

        <div class="panelCard">
          <div class="sectionTitle">最近一次交付</div>
          <template v-if="latestDelivery">
            <div class="statusRow">
              <span class="statusLabel">模式</span>
              <span class="statusValue">{{ String(latestDelivery.mode || 'unknown') }}</span>
            </div>
            <div class="statusRow">
              <span class="statusLabel">状态</span>
              <span class="statusValue" :data-status="String(latestDelivery.status || 'idle')">{{ latestDeliveryStatusLabel }}</span>
            </div>
            <div class="statusRow">
              <span class="statusLabel">文件数</span>
              <span class="statusValue">{{ Number(latestDelivery.changed_file_count || 0) }}</span>
            </div>
            <div class="statusRow">
              <span class="statusLabel">验证</span>
              <span class="statusValue">{{ latestDeliveryValidationLabel }}</span>
            </div>
            <div class="statusRow">
              <span class="statusLabel">说明</span>
              <span class="statusValue">{{ String(latestDelivery.summary || '') || '暂无说明' }}</span>
            </div>
            <div class="statusRow">
              <span class="statusLabel">预览地址</span>
              <a v-if="latestDeliveryPreviewUrl" class="previewLink" :href="latestDeliveryPreviewUrl" target="_blank" rel="noreferrer">
                {{ latestDeliveryPreviewUrl }}
              </a>
              <span v-else class="statusValue">暂无预览</span>
            </div>
            <div class="statusRow">
              <span class="statusLabel">部署地址</span>
              <a v-if="latestDeliveryDeployUrl" class="previewLink" :href="latestDeliveryDeployUrl" target="_blank" rel="noreferrer">
                {{ latestDeliveryDeployUrl }}
              </a>
              <span v-else class="statusValue">暂无部署</span>
            </div>
            <div v-if="latestDeliveryValidation?.details" class="hint">
              {{ String(latestDeliveryValidation.details || '') }}
            </div>
          </template>
          <div v-else class="statusValue">暂无交付记录</div>
        </div>
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
import type { Group, Message } from '../../api/groups'
import type { DeploymentJob } from '../../api/deployments'
import type { PreviewJob } from '../../api/previews'

const props = defineProps<{
  activeGroup: Group | null
  messages: Message[]
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

function messageMeta(message: Message) {
  try {
    return JSON.parse(String(message.metadata_json || '{}')) as Record<string, unknown>
  } catch {
    return {}
  }
}

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

const previewUpdatedAt = computed(() => {
  const value = props.previewJob?.updated_at
  if (!value) return '暂无记录'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
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

const latestDeliveryMeta = computed(() => {
  for (let index = props.messages.length - 1; index >= 0; index -= 1) {
    const meta = messageMeta(props.messages[index]!)
    const delivery = meta.delivery_result
    if (!delivery || typeof delivery !== 'object' || Array.isArray(delivery)) continue
    return meta
  }
  return null
})

const latestDelivery = computed(() => {
  const delivery = latestDeliveryMeta.value?.delivery_result
  if (!delivery || typeof delivery !== 'object' || Array.isArray(delivery)) return null
  return delivery as {
    mode?: unknown
    status?: unknown
    changed_file_count?: unknown
    validated?: unknown
    summary?: unknown
  }
})

const latestDeliveryValidation = computed(() => {
  const validation = latestDeliveryMeta.value?.validation_result
  if (!validation || typeof validation !== 'object' || Array.isArray(validation)) return null
  return validation as {
    ok?: unknown
    details?: unknown
  }
})

const latestDeliveryPreviewUrl = computed(() => {
  const preview = latestDeliveryMeta.value?.preview_result
  if (!preview || typeof preview !== 'object' || Array.isArray(preview)) return ''
  return String((preview as { url?: unknown }).url || '')
})

const latestDeliveryDeployUrl = computed(() => {
  const deploy = latestDeliveryMeta.value?.deploy_result
  if (!deploy || typeof deploy !== 'object' || Array.isArray(deploy)) return ''
  return String((deploy as { url?: unknown }).url || '')
})

const latestDeliveryStatusLabel = computed(() => {
  const status = String(latestDelivery.value?.status || '')
  if (status === 'succeeded') return '已完成'
  if (status === 'partial') return '部分完成'
  if (status === 'failed') return '失败'
  return '暂无记录'
})

const latestDeliveryValidationLabel = computed(() => {
  if (!latestDeliveryValidation.value) return '未验证'
  if (String(latestDelivery.value?.status || '') === 'failed' && Number(latestDelivery.value?.changed_file_count || 0) === 0) {
    return '未写入文件'
  }
  return Boolean(latestDeliveryValidation.value.ok) ? '验证通过' : '验证失败'
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
.heroCard {
  background:
    radial-gradient(circle at top right, color-mix(in srgb, var(--ah-primary-ghost) 40%, transparent), transparent 48%),
    var(--ah-surface-soft);
}
.deployCard {
  background: linear-gradient(180deg, color-mix(in srgb, var(--ah-bg) 92%, white), var(--ah-surface-soft));
}
.sectionTitle {
  font-size: 14px;
  font-weight: 900;
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
.deployHeader {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
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
