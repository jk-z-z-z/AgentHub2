<template>
  <div class="contactsPage">
    <section class="contactsListPanel">
      <div class="panelHeader">
        <div>
          <div class="eyebrow">Contacts</div>
          <div class="panelTitle">通讯录</div>
          <div class="panelSub">搜索联系人并快速进入会话。</div>
        </div>
        <div class="countPill">{{ visibleUsers.length }}</div>
      </div>

      <el-input v-model="searchKeywordModel" class="searchBar" placeholder="搜索联系人" clearable>
        <template #prefix>
          <el-icon class="searchIcon">
            <Search />
          </el-icon>
        </template>
      </el-input>

      <div class="sectionTitle">
        <span>联系人</span>
        <span v-if="loading" class="sectionHint">加载中…</span>
        <span v-else class="sectionHint">{{ visibleUsers.length }} 人</span>
      </div>

      <div v-if="loading" class="stateBlock">
        <el-skeleton :rows="7" animated />
      </div>
      <div v-else-if="listError" class="stateBlock stateError">
        <div class="stateTitle">联系人加载失败</div>
        <div class="stateText">{{ listError }}</div>
        <el-button class="stateAction" type="primary" plain @click="$emit('load-contacts')">重试</el-button>
      </div>
      <div v-else-if="visibleUsers.length === 0" class="stateBlock">
        <el-empty description="没有匹配的联系人" />
      </div>
      <div v-else class="contactList">
        <button
          v-for="user in visibleUsers"
          :key="user.id"
          class="contactRow"
          :class="{ active: selectedUser?.id === user.id, self: user.id === currentUserId }"
          @click="$emit('select-user', user.id)"
        >
          <div class="avatar">{{ avatarText(user) }}</div>
          <div class="contactMeta">
            <div class="contactTop">
              <div class="contactName">{{ displayName(user) }}</div>
              <span v-if="user.id === currentUserId" class="tag">我</span>
            </div>
            <div class="contactBottom">
              <span class="contactLine">{{ user.username }}</span>
              <span class="dot">·</span>
              <span class="contactLine">{{ user.role }}</span>
            </div>
          </div>
        </button>
      </div>
    </section>

    <section class="detailPanel">
      <template v-if="selectedUser">
        <div class="detailCard">
          <div class="detailHero">
            <div class="detailAvatar">{{ avatarText(selectedUser) }}</div>
            <div class="detailHeroMeta">
              <div class="detailNameRow">
                <div class="detailName">{{ displayName(selectedUser) }}</div>
                <span v-if="selectedUser.id === currentUserId" class="heroTag">当前账号</span>
              </div>
              <div class="detailUser">{{ selectedUser.username }}</div>
              <div class="detailEmail">{{ selectedUser.email }}</div>
            </div>
            <button class="detailArrowBtn" type="button" aria-label="进入详细信息" @click="detailOpenModel = true">
              <el-icon>
                <ArrowRight />
              </el-icon>
            </button>
          </div>

          <div class="detailSection">
            <div class="detailSectionTitle">基础信息</div>
            <div class="detailGrid">
              <div class="kv">
                <div class="k">用户名</div>
                <div class="v">{{ selectedUser.username }}</div>
              </div>
              <div class="kv">
                <div class="k">邮箱</div>
                <div class="v">{{ selectedUser.email }}</div>
              </div>
              <div class="kv">
                <div class="k">角色</div>
                <div class="v">{{ selectedUser.role }}</div>
              </div>
              <div class="kv">
                <div class="k">状态</div>
                <div class="v">{{ selectedUser.status }}</div>
              </div>
            </div>
          </div>

          <div class="detailSection">
            <div class="detailSectionTitle">个人简介</div>
            <div class="bioBox">
              <template v-if="selectedUser.bio">
                {{ selectedUser.bio }}
              </template>
              <template v-else>暂无简介。</template>
            </div>
          </div>

          <div class="detailSection detailFooter">
            <div class="detailTip">立刻联系会创建一个新的单聊会话，并跳转到消息页。</div>
            <el-button
              type="primary"
              class="contactBtn"
              :loading="contacting"
              :disabled="selectedUser.id === currentUserId"
              @click="$emit('contact-now')"
            >
              立刻联系
            </el-button>
          </div>
        </div>
      </template>
      <div v-else class="emptyPanel">
        <el-empty description="选择一个联系人查看详情" />
      </div>
    </section>

    <el-drawer v-model="detailOpenModel" title="联系人详细信息" direction="rtl" size="380px" :destroy-on-close="true">
      <template v-if="selectedUser">
        <div class="drawerHero">
          <div class="drawerAvatar">{{ avatarText(selectedUser) }}</div>
          <div class="drawerMeta">
            <div class="drawerName">{{ displayName(selectedUser) }}</div>
            <div class="drawerSub">{{ selectedUser.username }}</div>
          </div>
        </div>

        <div class="drawerSection">
          <div class="drawerTitle">基础字段</div>
          <div class="drawerRows">
            <div class="drawerRow"><span>用户名</span><span>{{ selectedUser.username }}</span></div>
            <div class="drawerRow"><span>邮箱</span><span>{{ selectedUser.email }}</span></div>
            <div class="drawerRow"><span>角色</span><span>{{ selectedUser.role }}</span></div>
            <div class="drawerRow"><span>状态</span><span>{{ selectedUser.status }}</span></div>
          </div>
        </div>

        <div class="drawerSection">
          <div class="drawerTitle">个人简介</div>
          <div class="drawerBio">{{ selectedUser.bio || '暂无简介。' }}</div>
        </div>

        <div class="drawerSection">
          <div class="drawerTitle">时间信息</div>
          <div class="drawerRows">
            <div class="drawerRow"><span>创建时间</span><span>{{ formatDate(selectedUser.created_at) }}</span></div>
            <div class="drawerRow"><span>更新时间</span><span>{{ formatDate(selectedUser.updated_at) }}</span></div>
          </div>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ArrowRight, Search } from '@element-plus/icons-vue'
import type { User } from '../../api/users'

const searchKeywordModel = defineModel<string>('searchKeyword', { required: true })
const detailOpenModel = defineModel<boolean>('detailOpen', { required: true })

defineProps<{
  loading: boolean
  listError: string
  visibleUsers: User[]
  selectedUser: User | null
  currentUserId: string
  contacting: boolean
}>()

defineEmits<{
  (e: 'load-contacts'): void
  (e: 'select-user', userId: string): void
  (e: 'contact-now'): void
}>()

function displayName(user: User) {
  return user.display_name || user.username || user.email || '未命名联系人'
}

function avatarText(user: User) {
  const label = displayName(user).trim()
  return (label || 'U').slice(0, 1).toUpperCase()
}

function formatDate(value: string) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}
</script>

<style scoped>
.contactsPage {
  height: calc(100vh - 36px);
  display: grid;
  grid-template-columns: 340px minmax(0, 1fr);
  gap: 12px;
  min-width: 0;
}
.contactsListPanel,
.detailPanel {
  min-width: 0;
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 18px;
  backdrop-filter: blur(10px);
  overflow: hidden;
}
.contactsListPanel {
  display: flex;
  flex-direction: column;
  padding: 16px;
}
.panelHeader { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; margin-bottom:12px; }
.eyebrow { font-size:12px; font-weight:800; letter-spacing:0.12em; text-transform:uppercase; color:rgba(31,35,41,.48); }
.panelTitle { margin-top:4px; font-size:22px; line-height:1.2; font-weight:900; color:rgba(31,35,41,.96); }
.panelSub { margin-top:6px; font-size:12px; color:rgba(31,35,41,.56); }
.countPill { flex:0 0 auto; height:30px; padding:0 12px; border-radius:999px; background:rgba(79,140,255,.1); color:#2563eb; font-size:12px; font-weight:800; display:inline-flex; align-items:center; }
.searchBar { margin-bottom:14px; }
.searchBar :deep() { height:38px; border-radius:12px; box-shadow:none; background:rgba(31,35,41,.04); }
.searchBar :deep() { box-shadow:0 0 0 1px rgba(79,140,255,.35) inset; }
.searchIcon { color:rgba(31,35,41,.42); }
.sectionTitle { display:flex; align-items:center; justify-content:space-between; margin-bottom:10px; font-size:13px; font-weight:800; color:rgba(31,35,41,.84); }
.sectionHint { color:rgba(31,35,41,.46); font-weight:600; }
.stateBlock { padding:12px 4px 4px; }
.stateError { display:grid; gap:10px; }
.stateTitle { font-size:14px; font-weight:800; color:rgba(31,35,41,.9); }
.stateText { font-size:13px; line-height:1.6; color:rgba(31,35,41,.58); word-break:break-all; }
.stateAction { justify-self:start; }
.contactList { display:grid; gap:8px; overflow:auto; padding-right:2px; }
.contactRow { width:100%; border:0; border-radius:14px; background:rgba(255,255,255,.7); padding:12px 12px 12px 10px; cursor:pointer; display:flex; align-items:center; gap:12px; text-align:left; color:inherit; transition:background .14s ease, transform .14s ease, box-shadow .14s ease; }
.contactRow:hover { background:rgba(79,140,255,.08); transform:translateY(-1px); }
.contactRow.active { background:linear-gradient(135deg, rgba(79,140,255,.14), rgba(79,140,255,.06)); box-shadow:inset 0 0 0 1px rgba(79,140,255,.18); }
.contactRow.self { opacity:.9; }
.avatar,.detailAvatar,.drawerAvatar { flex:0 0 auto; display:grid; place-items:center; border-radius:50%; background:linear-gradient(135deg,#4f8cff,#78a7ff); color:#fff; font-weight:900; }
.avatar { width:40px; height:40px; font-size:15px; }
.contactMeta { min-width:0; flex:1; }
.contactTop,.contactBottom,.detailNameRow { display:flex; align-items:center; gap:8px; }
.contactTop { justify-content:space-between; }
.contactName,.detailName { font-size:14px; font-weight:800; color:rgba(31,35,41,.94); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.tag,.heroTag { flex:0 0 auto; height:20px; padding:0 8px; border-radius:999px; display:inline-flex; align-items:center; justify-content:center; font-size:11px; font-weight:800; background:rgba(31,35,41,.06); color:rgba(31,35,41,.62); }
.contactBottom,.detailUser,.detailEmail { margin-top:4px; color:rgba(31,35,41,.56); font-size:12px; }
.dot { opacity:.4; }
.detailPanel { padding:14px; display:flex; min-height:0; }
.detailCard { width:100%; display:flex; flex-direction:column; gap:12px; }
.detailHero { display:grid; grid-template-columns:56px minmax(0,1fr) auto; gap:12px; align-items:center; padding:14px 14px 12px; border-radius:18px; background:linear-gradient(135deg, rgba(79,140,255,.12), rgba(255,255,255,.92)); border:1px solid rgba(79,140,255,.12); }
.detailAvatar { width:56px; height:56px; font-size:20px; }
.detailNameRow { justify-content:flex-start; }
.detailArrowBtn { width:36px; height:36px; border:0; border-radius:12px; background:rgba(31,35,41,.06); cursor:pointer; display:inline-flex; align-items:center; justify-content:center; color:rgba(31,35,41,.78); }
.detailSection { padding:14px; border-radius:16px; background:rgba(255,255,255,.72); border:1px solid rgba(31,35,41,.06); }
.detailSectionTitle { font-size:13px; font-weight:900; }
.detailGrid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; margin-top:12px; }
.kv { padding:10px 12px; border-radius:12px; background:rgba(31,35,41,.03); }
.k { font-size:12px; color:rgba(31,35,41,.5); font-weight:800; }
.v { margin-top:4px; font-size:13px; color:rgba(31,35,41,.84); word-break:break-all; }
.bioBox { margin-top:10px; font-size:13px; line-height:1.7; color:rgba(31,35,41,.78); white-space:pre-wrap; }
.detailFooter { display:flex; align-items:center; justify-content:space-between; gap:12px; }
.detailTip { font-size:12px; color:rgba(31,35,41,.56); line-height:1.5; }
.contactBtn { flex:0 0 auto; }
.emptyPanel { flex:1; display:flex; align-items:center; justify-content:center; }
.drawerHero { display:flex; align-items:center; gap:12px; margin-bottom:14px; }
.drawerAvatar { width:52px; height:52px; font-size:18px; }
.drawerName { font-weight:900; }
.drawerSub { font-size:12px; opacity:.62; }
.drawerSection { margin-top:14px; }
.drawerTitle { font-size:13px; font-weight:900; margin-bottom:8px; }
.drawerRows { display:grid; gap:8px; }
.drawerRow { display:flex; justify-content:space-between; gap:12px; font-size:13px; padding:10px 12px; border-radius:12px; background:rgba(31,35,41,.03); }
.drawerBio { font-size:13px; line-height:1.7; color:rgba(31,35,41,.78); white-space:pre-wrap; }
@media (max-width: 1180px) { .contactsPage { grid-template-columns:1fr; } }
</style>
