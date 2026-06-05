<template>
  <ProfileWorkspace
    :user="user"
    :saving-user="savingUser"
    :saving-profile-md="savingProfileMd"
    v-model:display-name="form.display_name"
    v-model:bio="form.bio"
    v-model:profile-md="profileMd"
    @save-user="saveUser"
    @save-profile-md="saveProfileMd"
  />
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  apiGetCurrentUser,
  apiGetCurrentUserProfileMd,
  apiUpdateCurrentUser,
  apiUpdateCurrentUserProfileMd,
  type User,
} from '../api/users'
import ProfileWorkspace from '../components/profile/ProfileWorkspace.vue'

const user = ref<User | null>(null)
const savingUser = ref(false)
const savingProfileMd = ref(false)
const profileMd = ref('')
const form = reactive({
  display_name: '',
  bio: '',
})

async function load() {
  const [userRes, profileRes] = await Promise.all([apiGetCurrentUser(), apiGetCurrentUserProfileMd()])
  user.value = userRes.data
  form.display_name = userRes.data.display_name || ''
  form.bio = userRes.data.bio || ''
  profileMd.value = profileRes.data.content || ''
}

async function saveUser() {
  savingUser.value = true
  try {
    const res = await apiUpdateCurrentUser({
      display_name: form.display_name.trim() || null,
      bio: form.bio.trim() || null,
    })
    user.value = res.data
    form.display_name = res.data.display_name || ''
    form.bio = res.data.bio || ''
    ElMessage.success('基础资料已保存')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : String(e))
  } finally {
    savingUser.value = false
  }
}

async function saveProfileMd() {
  savingProfileMd.value = true
  try {
    const res = await apiUpdateCurrentUserProfileMd(profileMd.value)
    profileMd.value = res.data.content || ''
    ElMessage.success('用户画像已保存')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : String(e))
  } finally {
    savingProfileMd.value = false
  }
}

onMounted(load)
</script>
