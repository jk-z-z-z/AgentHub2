import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

export type ThemeMode = 'light' | 'dark'

const THEME_STORAGE_KEY = 'agenthub-theme'

function normalizeTheme(value: string | null | undefined): ThemeMode {
  return value === 'dark' ? 'dark' : 'light'
}

export function getStoredTheme(): ThemeMode {
  if (typeof window === 'undefined') return 'light'
  return normalizeTheme(window.localStorage.getItem(THEME_STORAGE_KEY))
}

export function applyThemeToDocument(theme: ThemeMode) {
  if (typeof document === 'undefined') return
  const root = document.documentElement
  root.dataset.theme = theme
  root.style.colorScheme = theme
  document.body.dataset.theme = theme
}

export function persistTheme(theme: ThemeMode) {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(THEME_STORAGE_KEY, theme)
}

export const useThemeStore = defineStore('theme', () => {
  const theme = ref<ThemeMode>(getStoredTheme())

  const isDark = computed(() => theme.value === 'dark')

  function setTheme(nextTheme: ThemeMode) {
    theme.value = nextTheme
    persistTheme(nextTheme)
    applyThemeToDocument(nextTheme)
  }

  function toggleTheme() {
    setTheme(theme.value === 'dark' ? 'light' : 'dark')
  }

  return {
    theme,
    isDark,
    setTheme,
    toggleTheme,
  }
})
