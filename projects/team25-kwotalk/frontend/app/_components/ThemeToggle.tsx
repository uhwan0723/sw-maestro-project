'use client'

import { Moon, Sun } from 'lucide-react'
import { useSyncExternalStore } from 'react'

type Theme = 'light' | 'dark'
const storageKey = 'theme'

function isTheme (value: string | null): value is Theme {
  return value === 'light' || value === 'dark'
}

function getSystemTheme (): Theme {
  if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark'
  }

  return 'light'
}

// overridng 있는 경우 반영, 없으면 시스템
function getCurrentTheme (): Theme {
  const selectedTheme = document.documentElement.dataset.theme ?? null

  if (isTheme(selectedTheme)) {
    return selectedTheme
  }

  return getSystemTheme()
}

// 다른 탭에서 테마 변경 시 동기화
function syncStoredTheme () {
  const storedTheme = localStorage.getItem(storageKey)

  if (isTheme(storedTheme)) {
    document.documentElement.dataset.theme = storedTheme
  }
}

function subscribeToTheme (onThemeChange: () => void) {
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

  function handleThemeChange () {
    onThemeChange()
  }

  function handleStorageChange () {
    syncStoredTheme()
    onThemeChange()
  }

  mediaQuery.addEventListener('change', handleThemeChange)
  window.addEventListener('storage', handleStorageChange)
  window.addEventListener('themechange', handleThemeChange)

  return () => {
    mediaQuery.removeEventListener('change', handleThemeChange)
    window.removeEventListener('storage', handleStorageChange)
    window.removeEventListener('themechange', handleThemeChange)
  }
}

function applyTheme (theme: Theme) {
  document.documentElement.dataset.theme = theme
  localStorage.setItem(storageKey, theme)
  window.dispatchEvent(new Event('themechange'))
}

export default function ThemeToggle () {
  const theme = useSyncExternalStore(
    subscribeToTheme,
    getCurrentTheme,
    () => 'light'
  )

  function handleClick () {
    const nextTheme = theme === 'dark' ? 'light' : 'dark'

    applyTheme(nextTheme)
  }

  const isDark = theme === 'dark'
  const Icon = isDark ? Sun : Moon
  const label = isDark ? '라이트 모드로 전환' : '다크 모드로 전환'

  return (
    <button
      type='button'
      aria-label={label}
      title={label}
      onClick={handleClick}
      className={`flex h-10 w-fit cursor-pointer items-center gap-2 rounded-md px-3 
                  text-sm font-semibold text-app-muted transition-colors duration-200 
                  hover:bg-surface-muted hover:text-app-text`}
    >
      <Icon size={17} />
    </button>
  )
}
