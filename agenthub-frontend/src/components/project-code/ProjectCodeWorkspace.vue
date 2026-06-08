<template>
  <div class="page">
    <div class="shell">
      <WorkspacePanel :title="activeGroup?.name || '请选择项目'">
        <template #actions>
          <el-button class="heroRefresh" text :icon="RefreshRight" @click="$emit('reload')" :disabled="!activeGroupId" :loading="loading" />
          <el-dropdown trigger="click" :disabled="!activeGroupId">
            <el-button
              class="actionBtn iconActionBtn addSplitBtn"
              text
              :icon="Plus"
              :disabled="!activeGroupId"
              aria-label="新建"
              title="新建"
            />
            <template #dropdown>
              <el-dropdown-menu class="projectMenuCard">
                <el-dropdown-item @click="$emit('new-file')">
                  <span class="projectName">新建文件</span>
                </el-dropdown-item>
                <el-dropdown-item @click="$emit('new-dir')">
                  <span class="projectName">新建目录</span>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-dropdown trigger="click" @visible-change="projectMenuOpenModel = $event">
            <el-button class="toggleBtn" text :icon="ArrowDown" />
            <template #dropdown>
              <el-dropdown-menu class="projectMenuCard">
                <el-dropdown-item
                  v-for="g in projectGroups"
                  :key="g.id"
                  :class="{ active: g.id === activeGroupId }"
                  @click="$emit('select-project', g.id)"
                >
                  <span class="projectName">{{ g.name }}</span>
                  <span class="projectMark" v-if="g.id === activeGroupId">当前</span>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>

        <div class="treeWrap">
          <div v-if="!activeGroupId" class="empty">选择一个项目群聊后查看代码目录。</div>
          <div v-else-if="loading" class="empty">加载中…</div>
          <div v-else-if="treeRoots.length === 0" class="empty">当前 `shared/code` 目录还是空的。</div>
          <AgentFileTreeNode
            v-for="node in treeRoots"
            v-else
            :key="node.path"
            :node="node"
            :active-path="activePath"
            :open-dirs="openDirs"
            @open="$emit('open-file', $event)"
            @toggle="$emit('toggle-dir', $event)"
            @delete="$emit('delete-entry', $event)"
          />
        </div>
      </WorkspacePanel>

      <WorkspacePanel class="contentPanel">
        <div class="contentWrap">
          <CodeMirrorFileEditor
            v-if="activePath"
            :path="activePath"
            :content="activeContent"
            :dirty="isActiveDirty"
            :saving="saving"
            @update:content="$emit('update:content', $event)"
            @save="$emit('save-active')"
            @reset="$emit('reset')"
            @copy="$emit('copy')"
          />
          <div v-else class="empty">从左侧选择一个文件开始编辑。</div>
        </div>
      </WorkspacePanel>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineAsyncComponent } from 'vue'
import { ArrowDown, Plus, RefreshRight } from '@element-plus/icons-vue'
import type { Group } from '@/api/models.ts'
import AgentFileTreeNode, { type FileTreeNode } from '../AgentFileTreeNode.vue'
import WorkspacePanel from '../common/WorkspacePanel.vue'

const CodeMirrorFileEditor = defineAsyncComponent(() => import('../CodeMirrorFileEditor.vue'))

const projectMenuOpenModel = defineModel<boolean>('projectMenuOpen', { required: true })

defineProps<{
  activeGroup: Group | null
  activeGroupId: string
  projectGroups: Group[]
  loading: boolean
  treeRoots: FileTreeNode[]
  activePath: string
  openDirs: Record<string, boolean>
  activeContent: string
  isActiveDirty: boolean
  saving: boolean
}>()

defineEmits<{
  (e: 'reload'): void
  (e: 'select-project', groupId: string): void
  (e: 'open-file', path: string): void
  (e: 'toggle-dir', path: string): void
  (e: 'update:content', value: string): void
  (e: 'reset'): void
  (e: 'copy'): void
  (e: 'save-active'): void
  (e: 'new-file'): void
  (e: 'new-dir'): void
  (e: 'delete-entry', payload: { path: string; is_dir: boolean; label: string }): void
}>()
</script>

<style scoped>
.page { height: 100%; display:flex; flex-direction:column; min-height:0; }
.projectMenuCard { min-width: 240px; padding: 6px; }
.projectMenuCard :deep(.el-dropdown-menu__item) {
  display:flex;
  justify-content:space-between;
  align-items:center;
  gap:10px;
  border-radius:12px;
  margin: 4px 0;
}
.projectMenuCard :deep(.el-dropdown-menu__item:hover),
.projectMenuCard :deep(.el-dropdown-menu__item.active) { background:var(--ah-primary-ghost); color:var(--ah-text-primary); }
.projectName { min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.projectMark { flex:0 0 auto; font-size:12px; color:var(--ah-text-muted); }
.shell { flex:1; min-height:0; display:grid; grid-template-columns:340px minmax(0,1fr); gap:12px; }
.actionBtn {
  min-width: 84px;
}
.iconActionBtn {
  min-width: 32px;
  width: 32px;
  height: 32px;
  padding: 0;
}
.addSplitBtn {
  position: relative;
}
.treeWrap,.contentWrap { flex:1; min-height:0; overflow:auto; padding:12px 0 0; }
.contentWrap { min-height:0; display:flex; padding-top: 0; }
.empty { padding:18px 10px; color:var(--ah-text-tertiary); }
@media (max-width:1100px) { .shell { grid-template-columns:1fr; } }
</style>
