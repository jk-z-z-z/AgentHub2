<template>
  <div class="layout">
    <aside class="sider">
      <div class="brand">
        <div class="logo">AH</div>
        <div class="brandText">
          <div class="org">AgentHub</div>
          <div class="sub">企业工作台</div>
        </div>
      </div>

      <nav class="nav">
        <RouterLink class="navItem" :class="{ active: isActive('/messages') }" to="/messages">
          <span class="icon">💬</span>
          <span>消息</span>
        </RouterLink>
        <RouterLink class="navItem" :class="{ active: isActive('/profile') }" to="/profile">
          <span class="icon">🪪</span>
          <span>个人信息</span>
        </RouterLink>
        <RouterLink class="navItem" :class="{ active: isActive('/contacts') }" to="/contacts">
          <span class="icon">👥</span>
          <span>通讯录</span>
        </RouterLink>
        <RouterLink class="navItem" :class="{ active: isActive('/agents') }" to="/agents">
          <span class="icon">🤖</span>
          <span>智能体</span>
        </RouterLink>
        <RouterLink class="navItem" :class="{ active: isActive('/project-code') }" to="/project-code">
          <span class="icon">🗂</span>
          <span>项目代码</span>
        </RouterLink>
        <RouterLink class="navItem" :class="{ active: isActive('/admin/users') }" to="/admin/users">
          <span class="icon">🛠</span>
          <span>用户管理</span>
        </RouterLink>
      </nav>

      <div class="siderFooter">
        <div class="hint">基础导航</div>
        <button class="logout" @click="logout">退出登录</button>
      </div>
    </aside>

    <main class="main">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import { useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

function isActive(prefix: string) {
  return route.path === prefix || route.path.startsWith(prefix + '/')
}

async function logout() {
  localStorage.removeItem('token')
  await router.replace('/login')
}
</script>

<style scoped>
.layout {
  height: 100vh;
  width: 100vw;
  display: grid;
  grid-template-columns: 260px 1fr;
  background: var(--ah-bg);
  color: var(--ah-text);
}

.sider {
  background: #eef2fb;
  border-right: 1px solid rgba(31, 35, 41, 0.08);
  display: flex;
  flex-direction: column;
  padding: 18px 14px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 8px 14px 8px;
}
.logo {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-weight: 800;
  background: linear-gradient(135deg, #4f8cff, #7aa8ff);
  color: #fff;
  letter-spacing: 0.5px;
}
.brandText .org {
  font-size: 16px;
  font-weight: 700;
}
.brandText .sub {
  font-size: 12px;
  opacity: 0.7;
  margin-top: 2px;
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 10px;
}
.navItem {
  height: 44px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 12px;
  border-radius: 12px;
  color: inherit;
  text-decoration: none;
  opacity: 0.9;
}
.navItem:hover {
  background: rgba(79, 140, 255, 0.08);
}
.navItem.active {
  background: rgba(79, 140, 255, 0.14);
  opacity: 1;
}
.icon {
  width: 22px;
  display: inline-flex;
  justify-content: center;
}

.siderFooter {
  margin-top: auto;
  padding: 12px 8px 6px 8px;
  font-size: 12px;
  opacity: 0.6;
}
.logout {
  margin-top: 10px;
  width: 100%;
  height: 40px;
  border-radius: 12px;
  border: 1px solid rgba(31, 35, 41, 0.12);
  background: rgba(255, 255, 255, 0.75);
  cursor: pointer;
  font-weight: 800;
  color: rgba(31, 35, 41, 0.9);
}
.logout:hover {
  background: rgba(255, 255, 255, 0.9);
}

.main {
  overflow: hidden;
  padding: 18px;
}
</style>
