<template>
  <div class="page">
    <div class="hero">
      <div>
        <div class="eyebrow">Personal Space</div>
        <div class="title">个人信息</div>
        <div class="sub">维护你的基础资料和长期画像，智能体在私聊场景会读取这里的内容。</div>
      </div>
      <div class="heroCard">
        <div class="heroLabel">当前身份</div>
        <div class="heroName">{{ displayNameModel || user?.username || '未命名用户' }}</div>
        <div class="heroMeta">{{ user?.email || '-' }} · {{ user?.role || '-' }}</div>
      </div>
    </div>

    <div class="grid">
      <el-card class="panel" shadow="never">
        <div class="panelHeader">
          <div>
            <div class="panelTitle">基础资料</div>
            <div class="panelSub">会展示在通讯录、聊天成员名片和系统上下文里。</div>
          </div>
          <el-button type="primary" :loading="savingUser" @click="$emit('save-user')">保存资料</el-button>
        </div>

        <div class="formGrid">
          <div class="field">
            <div class="label">邮箱</div>
            <el-input :model-value="user?.email || ''" disabled />
          </div>
          <div class="field">
            <div class="label">用户名</div>
            <el-input :model-value="user?.username || ''" disabled />
          </div>
          <div class="field">
            <div class="label">显示名称</div>
            <el-input v-model="displayNameModel" placeholder="例如：沈涛 / 产品设计搭档" />
          </div>
          <div class="field">
            <div class="label">角色</div>
            <el-input :model-value="user?.role || ''" disabled />
          </div>
        </div>

        <div class="field">
          <div class="label">个人简介</div>
          <el-input
            v-model="bioModel"
            type="textarea"
            :rows="5"
            placeholder="介绍你的职责、专长、沟通偏好。"
          />
        </div>
      </el-card>

      <el-card class="panel" shadow="never">
        <div class="panelHeader">
          <div>
            <div class="panelTitle">用户画像 `PROFILE.md`</div>
            <div class="panelSub">建议写偏好、背景、习惯、技术方向，供私聊智能体长期记忆引用。</div>
          </div>
          <el-button :loading="savingProfileMd" @click="$emit('save-profile-md')">保存画像</el-button>
        </div>

        <div class="tips">
          <div class="tipTitle">建议结构</div>
          <div class="tipText">基本信息 / 技术偏好 / 工作方式 / 不喜欢的回答风格 / 当前重点项目</div>
        </div>

        <el-input
          v-model="profileMdModel"
          type="textarea"
          :rows="22"
          placeholder="# 用户档案&#10;&#10;## 基本信息&#10;- 职业：&#10;- 擅长：&#10;&#10;## 偏好&#10;- 回答风格："
        />
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { User } from '../../api/users'

defineProps<{
  user: User | null
  savingUser: boolean
  savingProfileMd: boolean
}>()

const displayNameModel = defineModel<string>('displayName', { required: true })
const bioModel = defineModel<string>('bio', { required: true })
const profileMdModel = defineModel<string>('profileMd', { required: true })

defineEmits<{
  (e: 'save-user'): void
  (e: 'save-profile-md'): void
}>()
</script>

<style scoped>
.page {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
  color: #1d2433;
}
.hero { display:grid; grid-template-columns:1.4fr 360px; gap:16px; padding:22px 24px; border-radius:24px; background: radial-gradient(circle at top left, rgba(255,207,122,.35), transparent 34%), radial-gradient(circle at right center, rgba(76,145,255,.24), transparent 32%), linear-gradient(135deg, #fff9ef 0%, #f3f7ff 100%); border:1px solid rgba(31,35,41,.08); }
.eyebrow { font-size:12px; text-transform:uppercase; letter-spacing:.14em; color:#7a6a44; font-weight:800; }
.title { margin-top:8px; font-size:30px; line-height:1.1; font-weight:900; }
.sub { margin-top:8px; max-width:720px; font-size:14px; line-height:1.7; color:rgba(29,36,51,.72); }
.heroCard { align-self:stretch; border-radius:20px; background:rgba(255,255,255,.74); border:1px solid rgba(31,35,41,.08); padding:18px; display:flex; flex-direction:column; justify-content:center; backdrop-filter:blur(10px); }
.heroLabel { font-size:12px; color:rgba(29,36,51,.56); }
.heroName { margin-top:8px; font-size:24px; font-weight:900; }
.heroMeta { margin-top:6px; font-size:13px; color:rgba(29,36,51,.64); }
.grid { flex:1; min-height:0; display:grid; grid-template-columns:minmax(360px,.92fr) minmax(420px,1.08fr); gap:16px; }
.panel { min-height:0; display:flex; flex-direction:column; background:rgba(255,255,255,.82); border-radius:22px; backdrop-filter:blur(12px); }
.panelHeader { display:flex; justify-content:space-between; align-items:flex-start; gap:16px; margin-bottom:16px; }
.panelTitle { font-size:18px; font-weight:900; }
.panelSub { margin-top:4px; font-size:12px; color:rgba(29,36,51,.6); }
.formGrid { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
.field { display:grid; gap:8px; margin-bottom:14px; }
.label { font-size:12px; font-weight:800; color:rgba(29,36,51,.68); }
.tips { margin-bottom:12px; padding:12px 14px; border-radius:16px; background:linear-gradient(135deg, rgba(255,246,214,.9), rgba(241,247,255,.9)); border:1px solid rgba(31,35,41,.06); }
.tipTitle { font-size:12px; font-weight:900; }
.tipText { margin-top:4px; font-size:12px; line-height:1.6; color:rgba(29,36,51,.68); }
@media (max-width:1180px) { .hero, .grid, .formGrid { grid-template-columns:1fr; } }
</style>
