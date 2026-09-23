<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { Avatar, FeatherIcon } from 'frappe-ui'
import { useAuth } from '@/composables/useAuth'
import { useRoleLabel } from '@/composables/useRoleLabel'
import { call } from '@/services/api'

const { currentUser } = useAuth()
const { roleLabel } = useRoleLabel()

const open = ref(false)
const menuRef = ref<HTMLElement | null>(null)

function handleOutsideClick(event: MouseEvent) {
  if (open.value && menuRef.value && !menuRef.value.contains(event.target as Node)) {
    open.value = false
  }
}
onMounted(() => document.addEventListener('click', handleOutsideClick))
onBeforeUnmount(() => document.removeEventListener('click', handleOutsideClick))

const loggingOut = ref(false)

// `logout` is a JSON API endpoint — navigating to it directly leaves the
// user staring at the raw response. Call it in the background, then do a
// full page load of the login page so all in-memory session state is dropped.
async function logout() {
  if (loggingOut.value) return
  loggingOut.value = true
  try {
    await call('logout')
  } catch {
    // Even if the request fails (e.g. session already expired), the user
    // asked to leave — send them to the login page regardless.
  }
  window.location.replace('/login')
}
</script>

<template>
  <div ref="menuRef" class="relative">
    <button
      class="flex w-full items-center gap-2.5 rounded-md p-1.5 text-left transition-colors hover:bg-canvas"
      @click="open = !open"
    >
      <Avatar :label="currentUser?.full_name || ''" size="sm" />
      <div class="min-w-0 flex-1">
        <p class="truncate text-sm font-medium text-charcoal">{{ currentUser?.full_name }}</p>
        <p class="truncate text-xs text-muted">{{ roleLabel }}</p>
      </div>
      <FeatherIcon name="chevron-up" class="h-3.5 w-3.5 shrink-0 text-muted" />
    </button>

    <Transition
      enter-active-class="transition duration-100 ease-out"
      leave-active-class="transition duration-75 ease-in"
      enter-from-class="opacity-0 translate-y-1"
      leave-to-class="opacity-0 translate-y-1"
    >
      <div
        v-if="open"
        class="absolute bottom-full left-0 z-20 mb-2 w-full min-w-[12rem] rounded-md border border-line bg-paper py-1 shadow-lg"
      >
        <RouterLink
          to="/sirb/profile"
          class="flex items-center gap-2 px-3 py-2 text-sm text-charcoal transition-colors hover:bg-canvas"
          @click="open = false"
        >
          <FeatherIcon name="user" class="h-4 w-4 text-muted" />
          Profile
        </RouterLink>
        <button
          class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-danger transition-colors hover:bg-canvas disabled:opacity-60"
          :disabled="loggingOut"
          @click="logout"
        >
          <FeatherIcon name="log-out" class="h-4 w-4" />
          Log out
        </button>
      </div>
    </Transition>
  </div>
</template>
