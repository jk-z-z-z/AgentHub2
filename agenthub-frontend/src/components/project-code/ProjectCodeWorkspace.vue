<template>
  <div class="page">
    <div class="shell">
      <section class="treePanel">
        <div class="panelHead">
          <div class="panelTitle">{{ activeGroup?.name || '请选择项目' }}</div>
          <div class="panelHeadActions">
            <el-button class="heroRefresh" :icon="RefreshRight" circle @click="$emit('reload')" :disabled="!activeGroupId" :loading="loading" />
            <el-popover
              v-model:visible="projectMenuOpenModel"
              placement="bottom-end"
              trigger="click"
              :width="260"
              :teleported="false"
              popper-class="projectMenuPopover"
            >
              <div class="projectMenuCard">
                <button
                  v-for="g in projectGroups"
                  :key="g.id"
                  class="projectOption"
                  :class="{ active: g.id === activeGroupId }"
                  @click="$emit('select-project', g.id)"
                >
                  <span class="projectName">{{ g.name }}</span>
                  <span class="projectMark" v-if="g.id === activeGroupId">当前</span>
                </button>
              </div>
              <template #reference>
                <el-button class="toggleBtn" :icon="ArrowDown" circle />
              </template>
            </el-popover>
          </div>
        </div>

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
          />
        </div>
      </section>

      <section class="contentPanel">
        <div class="contentWrap">
          <CodeMirrorFileEditor
            v-if="activePath"
            :path="activePath"
            :content="activeContent"
            :dirty="isActiveDirty"
            @update:content="$emit('update:content', $event)"
            @reset="$emit('reset')"
            @copy="$emit('copy')"
          />
          <div v-else class="empty">从左侧选择一个文件开始编辑。</div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ArrowDown, RefreshRight } from '@element-plus/icons-vue'
import type { Group } from '../../api/groups'
import AgentFileTreeNode, { type FileTreeNode } from '../AgentFileTreeNode.vue'
import { defineAsyncComponent } from 'vue'

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
}>()

defineEmits<{
  (e: 'reload'): void
  (e: 'select-project', groupId: string): void
  (e: 'open-file', path: string): void
  (e: 'toggle-dir', path: string): void
  (e: 'update:content', value: string): void
  (e: 'reset'): void
  (e: 'copy'): void
}>()
</script>

<style scoped>
.page { height: calc(100vh - 36px); display:flex; flex-direction:column; min-height:0; }
.panelHead { display:flex; align-items:center; justify-content:space-between; gap:10px; padding:14px 12px 10px; border-bottom:1px solid rgba(31,35,41,.06); }
.panelHeadActions { display:flex; gap:8px; align-items:center; }
.panelTitle { font-size:15px; font-weight:800; color:rgba(31,35,41,.86); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.projectMenuCard { display:flex; flex-direction:column; gap:6px; }
:global(.projectMenuPopover) { padding:10px; border-radius:16px; }
.projectOption { width:100%; display:flex; justify-content:space-between; align-items:center; gap:10px; border:0; border-radius:12px; padding:10px 12px; background:rgba(31,35,41,.03); color:rgba(31,35,41,.78); cursor:pointer; text-align:left; }
.projectOption:hover, .projectOption.active { background:rgba(64,158,255,.1); color:rgba(31,35,41,.92); }
.projectName { min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.projectMark { flex:0 0 auto; font-size:12px; color:rgba(31,35,41,.45); }
.shell { flex:1; min-height:0; display:grid; grid-template-columns:340px minmax(0,1fr); gap:12px; }
.treePanel,.contentPanel { height:100%; min-height:0; display:flex; flex-direction:column; border-radius:18px; background:rgba(255,255,255,.84); border:1px solid rgba(31,35,41,.08); backdrop-filter:blur(10px); }
.treeWrap,.contentWrap { flex:1; min-height:0; overflow:auto; padding:12px; }
.contentWrap { min-height:0; display:flex; }
.empty { padding:18px 10px; color:rgba(31,35,41,.58); }
@media (max-width:1100px) { .shell { grid-template-columns:1fr; } .treePanel,.contentPanel { height:auto; min-height:0; } }
</style>
