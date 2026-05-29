<script setup lang="ts">
defineProps<{ title?: string }>()
</script>

<template>
  <div class="app-layout">
    <slot />
  </div>
</template>

<style scoped>
.app-layout {
  height: 100vh;
  width: 100%;
}
</style>

