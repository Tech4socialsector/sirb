<script setup lang="ts">
import { ref } from 'vue'
import { Avatar, FeatherIcon } from 'frappe-ui'
import RoleNav from '@/components/navigation/RoleNav.vue'
import { useAuth } from '@/composables/useAuth'

const { currentUser } = useAuth()
const mobileOpen = ref(false)
</script>

<template>
  <div class="flex h-screen w-screen overflow-hidden bg-gray-50 text-gray-900">
    <!-- Desktop sidebar -->
    <aside class="hidden w-60 shrink-0 flex-col border-r border-gray-200 bg-white md:flex">
      <div class="flex h-14 items-center gap-2 border-b border-gray-100 px-4">
        <div class="flex h-7 w-7 items-center justify-center rounded-md bg-gray-900 text-xs font-bold text-white">
          IRB
        </div>
        <span class="text-sm font-semibold">SIRB</span>
      </div>
      <div class="flex-1 overflow-y-auto sirb-scrollbar">
        <RoleNav />
      </div>
      <div v-if="currentUser" class="flex items-center gap-2 border-t border-gray-100 p-3">
        <Avatar :label="currentUser.full_name" size="sm" />
        <div class="min-w-0">
          <p class="truncate text-sm font-medium">{{ currentUser.full_name }}</p>
          <p class="truncate text-xs text-gray-500">{{ currentUser.user }}</p>
        </div>
      </div>
    </aside>

    <!-- Mobile drawer -->
    <div v-if="mobileOpen" class="fixed inset-0 z-40 md:hidden" @click.self="mobileOpen = false">
      <div class="absolute inset-0 bg-black/30" />
      <aside class="relative flex h-full w-64 flex-col bg-white shadow-xl">
        <div class="flex h-14 items-center justify-between border-b border-gray-100 px-4">
          <span class="text-sm font-semibold">SIRB</span>
          <button class="p-1 text-gray-500" @click="mobileOpen = false">
            <FeatherIcon name="x" class="h-5 w-5" />
          </button>
        </div>
        <div class="flex-1 overflow-y-auto" @click="mobileOpen = false">
          <RoleNav />
        </div>
      </aside>
    </div>

    <div class="flex min-w-0 flex-1 flex-col">
      <header class="flex h-14 shrink-0 items-center gap-3 border-b border-gray-200 bg-white px-4 md:px-6">
        <button class="p-1 text-gray-600 md:hidden" @click="mobileOpen = true">
          <FeatherIcon name="menu" class="h-5 w-5" />
        </button>
        <slot name="header">
          <span class="text-sm font-medium text-gray-500">SIRB</span>
        </slot>
      </header>
      <main class="flex-1 overflow-y-auto sirb-scrollbar">
        <div class="mx-auto max-w-7xl px-4 py-6 md:px-8">
          <slot />
        </div>
      </main>
    </div>
  </div>
</template>
