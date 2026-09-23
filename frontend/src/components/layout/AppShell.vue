<script setup lang="ts">
import { ref } from 'vue'
import Sidebar from './Sidebar.vue'
import TopHeader from './TopHeader.vue'
import ProjectTimelineDrawer from '@/components/project/ProjectTimelineDrawer.vue'

const mobileNavOpen = ref(false)
</script>

<template>
  <div class="flex h-screen w-screen overflow-hidden bg-canvas text-charcoal">
    <Sidebar />

    <!-- Mobile drawer -->
    <div v-if="mobileNavOpen" class="fixed inset-0 z-40 md:hidden" @click.self="mobileNavOpen = false">
      <div class="absolute inset-0 bg-charcoal/30" />
      <Sidebar mobile class="relative shadow-xl" @navigate="mobileNavOpen = false" />
    </div>

    <div class="flex min-w-0 flex-1 flex-col">
      <TopHeader @toggle-mobile-nav="mobileNavOpen = true" />
      <main class="flex-1 overflow-y-auto sirb-scrollbar">
        <div class="mx-auto max-w-7xl px-4 py-6 md:px-8">
          <slot />
        </div>
      </main>
    </div>

    <ProjectTimelineDrawer />
  </div>
</template>
