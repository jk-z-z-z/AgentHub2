<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'

const emit = defineEmits<{
  (e: 'logout'): void
}>()

const route = useRoute()
const router = useRouter()

const navItems = [
  { label: '消息', routeName: 'messages' },
  { label: '联系人', routeName: 'contacts' },
  { label: 'Agent', routeName: 'agents' },
] as const

function go(routeName: (typeof navItems)[number]['routeName']) {
  void router.push({ name: routeName })
}
</script>

<template>
  <aside class="app-rail">
    <div class="brand">AH</div>
    <button
      v-for="item in navItems"
      :key="item.routeName"
      class="nav-item"
      :class="{ active: route.name === item.routeName }"
      @click="go(item.routeName)"
    >
      {{ item.label }}
    </button>
    <button class="nav-item logout-item" @click="emit('logout')">退出登录</button>
  </aside>
</template>

<style scoped>
.app-rail {
  background: linear-gradient(180deg, #0d1b2a 0%, #15263b 100%);
  color: #e9f1ff;
  padding: 18px 12px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  align-items: center;
}

.brand {
  width: 46px;
  height: 46px;
  border-radius: 14px;
  background: linear-gradient(135deg, #4a90e2 0%, #77b7ff 100%);
  display: grid;
  place-items: center;
  font-weight: 800;
}

.nav-item {
  width: 100%;
  text-align: center;
  padding: 10px 8px;
  border-radius: 12px;
  font-size: 13px;
  color: rgba(233, 241, 255, 0.72);
  background: transparent;
  border: 0;
}

.nav-item.active {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.logout-item {
  margin-top: auto;
  color: #ffd7d7;
  background: rgba(255, 255, 255, 0.06);
}

.logout-item:hover {
  background: rgba(255, 255, 255, 0.1);
}
</style>
