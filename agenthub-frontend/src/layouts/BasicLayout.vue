<template>
  <div class="layout">
    <aside class="rail">
      <div class="railTop">
        <div class="railLogo">
          <img class="railLogoImg" :src="railLogoSrc" alt="agenthub-weon" />
        </div>

        <el-tooltip placement="right" effect="light" :show-after="0" :hide-after="0" :enterable="false">
          <template #content>
            <div class="tooltipContent">
              <div class="tooltipTitle">消息</div>
              <div class="tooltipDesc">查看会话列表与群聊消息</div>
            </div>
          </template>
          <RouterLink class="railBtn" :class="{ active: isActive('/messages') }" to="/messages" aria-label="消息">
            <el-icon>
              <ChatDotRound />
            </el-icon>
          </RouterLink>
        </el-tooltip>

        <el-tooltip placement="right" effect="light" :show-after="0" :hide-after="0" :enterable="false">
          <template #content>
            <div class="tooltipContent">
              <div class="tooltipTitle">通讯录</div>
              <div class="tooltipDesc">查看用户与成员信息</div>
            </div>
          </template>
          <RouterLink class="railBtn" :class="{ active: isActive('/contacts') }" to="/contacts" aria-label="通讯录">
            <el-icon>
              <User />
            </el-icon>
          </RouterLink>
        </el-tooltip>

        <el-tooltip placement="right" effect="light" :show-after="0" :hide-after="0" :enterable="false">
          <template #content>
            <div class="tooltipContent">
              <div class="tooltipTitle">智能体</div>
              <div class="tooltipDesc">管理智能体、模版与能力配置</div>
            </div>
          </template>
          <RouterLink class="railBtn" :class="{ active: isActive('/agents') }" to="/agents" aria-label="智能体">
            <el-icon>
              <Monitor />
            </el-icon>
          </RouterLink>
        </el-tooltip>

        <el-tooltip placement="right" effect="light" :show-after="0" :hide-after="0" :enterable="false">
          <template #content>
            <div class="tooltipContent">
              <div class="tooltipTitle">文件</div>
              <div class="tooltipDesc">浏览项目代码与工作区文件</div>
            </div>
          </template>
          <RouterLink class="railBtn" :class="{ active: isActive('/project-code') }" to="/project-code" aria-label="文件">
            <el-icon>
              <FolderOpened />
            </el-icon>
          </RouterLink>
        </el-tooltip>
      </div>

      <div class="railBottom">
        <el-tooltip placement="right" effect="light" :show-after="0" :hide-after="0" :enterable="false">
          <template #content>
            <div class="tooltipContent">
              <div class="tooltipTitle">{{ themeStore.isDark ? '切换到亮色' : '切换到深色' }}</div>
              <div class="tooltipDesc">{{ themeStore.isDark ? '恢复当前保留的亮色主题' : '进入深色主题模式' }}</div>
            </div>
          </template>
          <el-button
            class="themeBtn"
            text
            circle
            :aria-label="themeStore.isDark ? '切换到亮色主题' : '切换到深色主题'"
            @click="themeStore.toggleTheme()"
          >
            <el-icon>
              <component :is="themeStore.isDark ? Sunny : MoonNight" />
            </el-icon>
          </el-button>
        </el-tooltip>

        <el-popover
          v-model:visible="profilePopoverOpen"
          placement="top-end"
          trigger="click"
          :show-after="0"
          :hide-after="0"
          transition="none"
          :width="224"
          popper-class="profilePopover"
        >
          <template #reference>
            <el-button class="profileBtn" text circle aria-label="个人信息">
              <el-icon>
                <UserFilled />
              </el-icon>
            </el-button>
          </template>

          <div class="profileCard">
            <div class="profileTop">
              <div class="profileAvatar">{{ profileAvatar }}</div>
              <div class="profileMeta">
                <div class="profileName">{{ profileName }}</div>
                <div class="profileSub">{{ currentUser?.role || 'member' }}</div>
              </div>
              <el-button class="profileDetailBtn" text circle @click="goProfile" aria-label="进入个人信息详情">
                <el-icon>
                  <ArrowRightBold />
                </el-icon>
              </el-button>
            </div>

            <div v-if="userLoading" class="profileLoading">加载个人信息中…</div>
            <div v-else-if="userError" class="profileError">{{ userError }}</div>
            <template v-else>
              <div class="profileFields">
                <div class="profileRow">
                  <span class="label">用户名</span>
                  <span class="value">{{ currentUser?.username || '-' }}</span>
                </div>
                <div class="profileRow">
                  <span class="label">邮箱</span>
                  <span class="value">{{ currentUser?.email || '-' }}</span>
                </div>
                <div class="profileRow">
                  <span class="label">显示名称</span>
                  <span class="value">{{ currentUser?.display_name || '-' }}</span>
                </div>
              </div>
            </template>

            <el-button class="logoutRow" plain type="danger" @click="logout">
              <span>退出登录</span>
              <el-icon><SwitchButton /></el-icon>
            </el-button>
          </div>
        </el-popover>
      </div>
    </aside>

    <main class="main">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ChatDotRound,
  FolderOpened,
  Monitor,
  ArrowRightBold,
  MoonNight,
  Sunny,
  SwitchButton,
  User,
  UserFilled,
} from '@element-plus/icons-vue'
import { apiGetCurrentUser, type User as CurrentUser } from '../api/users'
import { useThemeStore } from '../stores/theme'
import railLogoSrc from '../assets/sidebar-logo-dog.png'

const route = useRoute()
const router = useRouter()
const themeStore = useThemeStore()

const currentUser = ref<CurrentUser | null>(null)
const userLoading = ref(false)
const userError = ref('')
const profilePopoverOpen = ref(false)

const profileName = computed(() => currentUser.value?.display_name || currentUser.value?.username || currentUser.value?.email || '个人信息')
const profileAvatar = computed(() => (profileName.value || 'P').slice(0, 1).toUpperCase())

function isActive(prefix: string) {
  return route.path === prefix || route.path.startsWith(prefix + '/')
}

async function loadCurrentUser() {
  userLoading.value = true
  userError.value = ''
  try {
    const result = await apiGetCurrentUser()
    currentUser.value = result.data
  } catch (error) {
    userError.value = error instanceof Error ? error.message : String(error)
  } finally {
    userLoading.value = false
  }
}

function goProfile() {
  profilePopoverOpen.value = false
  router.push('/profile')
}

async function logout() {
  profilePopoverOpen.value = false
  localStorage.removeItem('token')
  await router.replace('/login')
}

onMounted(loadCurrentUser)
</script>

<style scoped>
.layout {
  height: 100vh;
  width: 100%;
  display: grid;
  grid-template-columns: 68px 1fr;
  background: var(--ah-bg);
  color: var(--ah-text);
  overflow: hidden;
}

.rail {
  background: var(--ah-surface-ghost);
  border-right: 1px solid var(--ah-border);
  backdrop-filter: blur(10px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0 12px;
}

.railTop,
.railBottom {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.railLogo {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: var(--ah-surface-strong);
  overflow: hidden;
  box-shadow: var(--ah-shadow-sm);
  margin-bottom: 4px;
}
.railLogoImg {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.railBtn,
.profileBtn {
  width: 46px;
  height: 46px;
  border-radius: 14px;
  background: transparent;
  color: var(--ah-text-muted);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  font-size: 22px;
}

.railBtn:hover,
.profileBtn:hover {
  background: var(--ah-hover);
  color: var(--ah-text-secondary);
}

.railBtn.active {
  background: var(--ah-active);
  color: var(--ah-text-primary);
}

.main {
  height: 100%;
  overflow: hidden;
  padding: 18px;
  min-width: 0;
  min-height: 0;
}

.tooltipContent {
  padding: 2px 2px 1px;
  min-width: 132px;
}
.tooltipTitle {
  font-size: 13px;
  font-weight: 800;
  color: var(--ah-text-primary);
}
.tooltipDesc {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.4;
  color: var(--ah-text-tertiary);
}

.profileCard {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.profileTop {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--ah-border);
}
.profileAvatar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: var(--ah-avatar-gradient);
  color: var(--ah-text-on-primary);
  font-weight: 900;
}
.profileMeta {
  min-width: 0;
  flex: 1;
}
.profileDetailBtn {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  color: var(--ah-text-secondary);
  flex: 0 0 auto;
}
.profileName {
  font-size: 14px;
  font-weight: 900;
}
.profileSub {
  margin-top: 4px;
  font-size: 12px;
  color: var(--ah-text-tertiary);
}
.profileFields {
  display: grid;
  gap: 10px;
}
.profileRow {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 13px;
  line-height: 1.4;
}
.profileRow .label {
  color: var(--ah-text-muted);
  flex: 0 0 auto;
}
.profileRow .value {
  color: var(--ah-text-primary);
  text-align: right;
  word-break: break-all;
  flex: 1;
}
.profileLoading,
.profileError {
  font-size: 12px;
  color: var(--ah-text-tertiary);
}
.profileError {
  color: var(--ah-danger);
}
.logoutRow {
  margin-top: auto;
  height: 42px;
  border-radius: 12px;
  justify-content: space-between;
  font-size: 13px;
  font-weight: 700;
}

.themeBtn {
  width: 46px;
  height: 46px;
  border-radius: 14px;
  background: transparent;
  color: var(--ah-text-muted);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  font-size: 22px;
}

.themeBtn:hover {
  background: var(--ah-hover);
  color: var(--ah-text-secondary);
}
</style>
