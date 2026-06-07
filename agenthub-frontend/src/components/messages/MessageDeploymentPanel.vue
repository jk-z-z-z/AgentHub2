<template>
  <div class="sidePanel">
    <div class="sideHeader">
      <div>
        <div class="sideTitle">部署</div>
        <div class="sideSubtitle">{{ activeGroup?.name || '未选择会话' }}</div>
      </div>
      <button class="sideCloseBtn" type="button" aria-label="关闭部署面板" @click="$emit('close')">
        <el-icon>
          <Close />
        </el-icon>
      </button>
    </div>

    <div class="sideBody">
      <div v-if="activeGroup?.type === 'project'" class="deployShell">
        <div class="panelCard">
          <div class="sectionTitle">当前预览</div>
          <div class="toolbar">
            <el-button
              v-if="previewJob?.url"
              size="small"
              type="primary"
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
            <a v-if="previewJob?.url" class="previewLink" :href="previewJob.url" target="_blank" rel="noreferrer">{{ previewJob.url }}</a>
            <span v-else class="statusValue">暂无预览</span>
          </div>
          <div class="statusRow">
            <span class="statusLabel">最近刷新</span>
            <span class="statusValue">{{ previewUpdatedAt }}</span>
          </div>
          <div v-if="previewJob?.error_message" class="errBox">{{ previewJob.error_message }}</div>
        </div>

        <div class="panelCard">
          <div class="toolbar">
            <el-button size="small" type="primary" :loading="deployPending" @click="submitDeploy">
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
          <div class="hint">
            和任务规划、文件目录保持同一层级，在群组对话里直接发起部署。
          </div>
          <div class="statusRow">
            <span class="statusLabel">状态</span>
            <span class="statusValue" :data-status="deploymentTone">{{ deploymentLabel }}</span>
          </div>
          <div class="statusRow">
            <span class="statusLabel">Dockerfile</span>
            <span class="statusValue">{{ hasDockerfile ? '已检测到' : '未检测到' }}</span>
          </div>
          <div class="statusRow">
            <span class="statusLabel">预览地址</span>
            <a v-if="previewUrl" class="previewLink" :href="previewUrl" target="_blank" rel="noreferrer">{{ previewUrl }}</a>
            <span v-else class="statusValue">部署后生成</span>
          </div>
        </div>

        <div class="panelCard">
          <div class="sectionTitle">部署参数</div>
          <div class="formGrid">
            <label class="field">
              <span>镜像名</span>
              <el-input v-model="draft.imageRef" placeholder="agenthub/my-project:latest" />
            </label>
            <label class="field">
              <span>容器名</span>
              <el-input v-model="draft.containerName" placeholder="agenthub-my-project" />
            </label>
            <label class="field">
              <span>Dockerfile</span>
              <el-input v-model="draft.dockerfilePath" placeholder="Dockerfile" />
            </label>
            <label class="field">
              <span>构建上下文</span>
              <el-input v-model="draft.buildContextPath" placeholder="." />
            </label>
          </div>
        </div>

        <div class="panelCard">
          <div class="sectionTitle">运行配置</div>
          <div class="formGrid">
            <label class="field">
              <span>宿主端口</span>
              <el-input-number v-model="draft.hostPort" :min="1" :max="65535" controls-position="right" />
            </label>
            <label class="field">
              <span>容器端口</span>
              <el-input-number v-model="draft.containerPort" :min="1" :max="65535" controls-position="right" />
            </label>
          </div>
          <label class="field">
            <span>启动命令</span>
            <el-input v-model="draft.containerCommand" placeholder="可选，例如 npm run start" />
          </label>
          <label class="field">
            <span>安装命令</span>
            <el-input v-model="draft.installCommand" placeholder="例如 npm install" />
          </label>
          <label class="field">
            <span>测试命令</span>
            <el-input v-model="draft.testCommand" placeholder="例如 npm test" />
          </label>
          <label class="field">
            <span>构建命令</span>
            <el-input v-model="draft.buildCommand" placeholder="例如 npm run build" />
          </label>
        </div>

        <div class="panelCard">
          <div class="sectionTitle">环境变量</div>
          <label class="field">
            <span>每行一个 `KEY=VALUE`</span>
            <el-input v-model="envText" type="textarea" :rows="5" placeholder="NODE_ENV=production" />
          </label>
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
          <div v-if="deploymentJob.error_message" class="errBox">{{ deploymentJob.error_message }}</div>
          <details v-if="deploymentJob.logs_text" class="logDetails">
            <summary>查看日志</summary>
            <pre class="logBlock">{{ deploymentJob.logs_text }}</pre>
          </details>
        </div>
      </div>

      <div v-else class="sideEmpty">
        <div class="empty">仅项目群聊支持部署</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { Close } from '@element-plus/icons-vue'
import type { Group, ProjectCodeEntry } from '../../api/groups'
import type { DeploymentJob, DeploymentRequest } from '../../api/deployments'
import type { PreviewJob } from '../../api/previews'

type DeployDraft = {
  imageRef: string
  containerName: string
  dockerfilePath: string
  buildContextPath: string
  hostPort: number
  containerPort: number
  installCommand: string
  testCommand: string
  buildCommand: string
  containerCommand: string
}

const props = defineProps<{
  activeGroup: Group | null
  projectFilesEntries: ProjectCodeEntry[]
  previewJob: PreviewJob | null
  previewPending: boolean
  deploymentJob: DeploymentJob | null
  deployPending: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'close-preview'): void
  (e: 'deploy', payload: DeploymentRequest): void
  (e: 'retry-deploy', deploymentId: number): void
}>()

const draft = reactive<DeployDraft>({
  imageRef: '',
  containerName: '',
  dockerfilePath: 'Dockerfile',
  buildContextPath: '.',
  hostPort: 18080,
  containerPort: 80,
  installCommand: '',
  testCommand: '',
  buildCommand: '',
  containerCommand: '',
})
const envText = ref('')

function slugify(text: string) {
  return text
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 48) || 'project'
}

function buildDefaultPort(group: Group | null) {
  const workspaceId = Number(group?.workspace_id || 0)
  return workspaceId > 0 ? Math.min(65535, 18000 + workspaceId) : 18080
}

function portFromJob(job: DeploymentJob | null) {
  const ports = Array.isArray(job?.spec?.ports) ? job?.spec?.ports : []
  const firstPort = ports[0]
  if (!firstPort || typeof firstPort !== 'object') return null
  const hostPort = Number((firstPort as { host_port?: unknown }).host_port)
  return Number.isFinite(hostPort) && hostPort > 0 ? hostPort : null
}

function seedDraftFromContext() {
  const group = props.activeGroup
  if (!group) return

  if (props.deploymentJob) {
    const hostPort = portFromJob(props.deploymentJob) || buildDefaultPort(group)
    draft.imageRef = props.deploymentJob.image_ref || ''
    draft.containerName = props.deploymentJob.container_name || ''
    draft.dockerfilePath = props.deploymentJob.dockerfile_path || 'Dockerfile'
    draft.buildContextPath = props.deploymentJob.build_context_path || '.'
    draft.hostPort = hostPort
    draft.containerPort = 80
    draft.installCommand = String(props.deploymentJob.spec?.install_command || '')
    draft.testCommand = String(props.deploymentJob.spec?.test_command || '')
    draft.buildCommand = String(props.deploymentJob.spec?.build_command || '')
    draft.containerCommand = String(props.deploymentJob.spec?.container_command || '')
    const env = props.deploymentJob.spec?.env
    if (env && typeof env === 'object' && !Array.isArray(env)) {
      envText.value = Object.entries(env as Record<string, unknown>)
        .map(([key, value]) => `${key}=${String(value ?? '')}`)
        .join('\n')
    } else {
      envText.value = ''
    }
    return
  }

  const slug = slugify(group.name || 'project')
  draft.imageRef = `agenthub/${slug}:latest`
  draft.containerName = `agenthub-${slug}`
  draft.dockerfilePath = 'Dockerfile'
  draft.buildContextPath = '.'
  draft.hostPort = buildDefaultPort(group)
  draft.containerPort = 80
  draft.installCommand = ''
  draft.testCommand = ''
  draft.buildCommand = ''
  draft.containerCommand = ''
  envText.value = ''
}

const hasDockerfile = computed(() =>
  props.projectFilesEntries.some((entry) => {
    if (entry.is_dir) return false
    const normalized = String(entry.path || '').trim().toLowerCase()
    return normalized === 'dockerfile' || normalized.endsWith('/dockerfile')
  }),
)

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

const previewUrl = computed(() => {
  const hostPort = portFromJob(props.deploymentJob) || draft.hostPort
  if (!hostPort) return ''
  return `http://127.0.0.1:${hostPort}`
})

const shortContainerId = computed(() => {
  const containerId = props.deploymentJob?.deployed_container_id || ''
  return containerId ? containerId.slice(0, 12) : '尚未生成'
})

function parseEnvText() {
  const env: Record<string, string> = {}
  for (const rawLine of envText.value.split('\n')) {
    const line = rawLine.trim()
    if (!line) continue
    const divider = line.indexOf('=')
    if (divider <= 0) continue
    const key = line.slice(0, divider).trim()
    const value = line.slice(divider + 1).trim()
    if (!key) continue
    env[key] = value
  }
  return env
}

function submitDeploy() {
  if (!props.activeGroup) return
  emit('deploy', {
    workspace_id: Number(props.activeGroup.workspace_id),
    image_ref: draft.imageRef.trim(),
    container_name: draft.containerName.trim(),
    dockerfile_path: draft.dockerfilePath.trim() || 'Dockerfile',
    build_context_path: draft.buildContextPath.trim() || '.',
    install_command: draft.installCommand.trim() || null,
    test_command: draft.testCommand.trim() || null,
    build_command: draft.buildCommand.trim() || null,
    container_command: draft.containerCommand.trim() || null,
    env: parseEnvText(),
    ports: [
      {
        host_port: Number(draft.hostPort),
        container_port: Number(draft.containerPort),
        protocol: 'tcp',
      },
    ],
  })
}

watch(
  () => [props.activeGroup?.id, props.deploymentJob?.id, props.deploymentJob?.updated_at],
  () => {
    seedDraftFromContext()
  },
  { immediate: true },
)
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
.deployShell {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.panelCard {
  padding: 14px;
  border-radius: 16px;
  border: 1px solid rgba(31, 35, 41, 0.06);
  background: rgba(255, 255, 255, 0.78);
}
.toolbar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
.hint {
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(79, 140, 255, 0.08);
  color: rgba(31, 35, 41, 0.68);
  font-size: 12px;
  line-height: 1.5;
  margin-bottom: 12px;
}
.sectionTitle {
  font-size: 13px;
  font-weight: 900;
  margin-bottom: 12px;
}
.formGrid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.field + .field {
  margin-top: 12px;
}
.field span {
  font-size: 12px;
  color: rgba(31, 35, 41, 0.68);
  font-weight: 700;
}
.statusRow {
  display: grid;
  grid-template-columns: 72px 1fr;
  gap: 10px;
  align-items: start;
  font-size: 12px;
  margin-top: 10px;
}
.statusLabel {
  color: rgba(31, 35, 41, 0.54);
  font-weight: 700;
}
.statusValue {
  color: rgba(31, 35, 41, 0.88);
  word-break: break-all;
}
.statusValue[data-status='succeeded'] {
  color: #207a32;
}
.statusValue[data-status='failed'] {
  color: #c2410c;
}
.statusValue[data-status='running'] {
  color: #1d4ed8;
}
.previewLink {
  color: #1d4ed8;
  text-decoration: none;
  word-break: break-all;
}
.previewLink:hover {
  text-decoration: underline;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  word-break: break-all;
}
.errBox {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 12px;
  background: #fff4f2;
  color: #d92d20;
  font-size: 12px;
  line-height: 1.5;
}
.logDetails {
  margin-top: 12px;
}
.logDetails summary {
  cursor: pointer;
  font-size: 12px;
  font-weight: 800;
  color: rgba(31, 35, 41, 0.72);
}
.logBlock {
  margin: 10px 0 0;
  padding: 12px;
  border-radius: 12px;
  background: #101826;
  color: #d8e4f3;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 240px;
  overflow: auto;
}
.sideEmpty {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.empty {
  color: rgba(31, 35, 41, 0.58);
}
@media (max-width: 720px) {
  .formGrid {
    grid-template-columns: 1fr;
  }
}
</style>
