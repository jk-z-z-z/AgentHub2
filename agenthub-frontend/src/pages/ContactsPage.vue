<template>
  <div class="shell">
    <section class="left">
      <div class="groupItem active">
        <div class="icon">👤</div>
        <div class="txt">
          <div class="t1">我的好友</div>
        </div>
      </div>
      <div class="groupItem">
        <div class="icon">➕</div>
        <div class="txt">
          <div class="t1">新的好友</div>
        </div>
      </div>
      <div class="groupItem">
        <div class="icon">📨</div>
        <div class="txt">
          <div class="t1">企业/团队邀请</div>
        </div>
      </div>
      <div class="groupItem">
        <div class="icon">🏢</div>
        <div class="txt">
          <div class="t1">创建或加入企业/团队</div>
        </div>
      </div>
    </section>

    <section class="right">
      <div class="header">
        <div class="title">我的好友</div>
        <button class="primary">添加好友</button>
      </div>
      <div class="list">
        <div v-if="loading" style="opacity: 0.6; padding: 10px 6px">加载中…</div>
        <div v-for="p in mockPeople" :key="p.name" class="person">
          <div class="avatar">{{ p.abbr }}</div>
          <div class="name">{{ p.name }}</div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { apiListUsers, type User } from '../api/agenthub'

const users = ref<User[]>([])
const loading = ref(false)

const mockPeople = computed(() =>
  users.value.map((u) => ({
    abbr: (u.display_name || u.username || u.email).slice(0, 1).toUpperCase(),
    name: u.display_name || u.username || u.email,
  })),
)

async function load() {
  loading.value = true
  try {
    const res = await apiListUsers()
    users.value = res.data
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.shell {
  height: calc(100vh - 36px);
  display: grid;
  grid-template-columns: 420px 1fr;
  gap: 14px;
}
.left,
.right {
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 18px;
  overflow: hidden;
}
.left {
  padding: 14px;
  display: grid;
  gap: 10px;
  align-content: start;
}
.groupItem {
  height: 72px;
  border-radius: 16px;
  padding: 12px;
  display: grid;
  grid-template-columns: 44px 1fr;
  gap: 12px;
  align-items: center;
  cursor: pointer;
}
.groupItem:hover {
  background: rgba(79, 140, 255, 0.06);
}
.groupItem.active {
  background: rgba(31, 35, 41, 0.06);
}
.icon {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  background: rgba(255, 176, 0, 0.18);
  font-weight: 900;
}
.t1 {
  font-weight: 900;
  font-size: 16px;
}

.header {
  height: 70px;
  padding: 0 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(31, 35, 41, 0.06);
}
.title {
  font-weight: 900;
  font-size: 18px;
}
.primary {
  height: 40px;
  padding: 0 18px;
  border-radius: 999px;
  border: 0;
  background: #2f6bff;
  color: #fff;
  font-weight: 900;
  cursor: pointer;
}
.list {
  padding: 14px;
  overflow: auto;
  height: calc(100% - 70px);
}
.person {
  height: 64px;
  border-radius: 16px;
  padding: 10px 12px;
  display: grid;
  grid-template-columns: 46px 1fr;
  gap: 12px;
  align-items: center;
}
.person:hover {
  background: rgba(79, 140, 255, 0.06);
}
.avatar {
  width: 46px;
  height: 46px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  background: rgba(79, 140, 255, 0.14);
  color: #2563eb;
  font-weight: 900;
}
.name {
  font-weight: 800;
}
</style>
