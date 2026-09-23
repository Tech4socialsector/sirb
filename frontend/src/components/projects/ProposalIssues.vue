<script setup lang="ts">
import { computed } from 'vue'
import { FeatherIcon } from 'frappe-ui'
import type { ProposalIssue } from '@/types/project'

const props = defineProps<{ issues: ProposalIssue[] }>()
const emit = defineEmits<{ jump: [ProposalIssue]; close: [] }>()

// Group by tab, keeping the form's own order so the list reads top to bottom.
const groups = computed(() => {
  const out: { tab: string; items: ProposalIssue[] }[] = []
  for (const issue of props.issues) {
    const tab = issue.tab_label || 'Basic details'
    let g = out.find((x) => x.tab === tab)
    if (!g) out.push((g = { tab, items: [] }))
    g.items.push(issue)
  }
  return out
})
</script>

<template>
  <div role="alert" class="rounded-lg border border-danger/30 bg-danger/5 p-5">
    <div class="mb-3 flex items-start gap-3">
      <FeatherIcon name="alert-circle" class="mt-0.5 h-5 w-5 shrink-0 text-danger" />
      <div class="min-w-0 flex-1">
        <p class="text-sm font-semibold text-charcoal">
          Your proposal isn't ready to submit yet — {{ issues.length }}
          {{ issues.length === 1 ? 'question needs' : 'questions need' }} an answer.
        </p>
        <p class="mt-0.5 text-sm text-muted">
          Your answers so far are saved. Click an item to go straight to it; it's ticked off here as soon as you answer
          it.
        </p>
      </div>
      <button class="rounded-md p-1 text-muted hover:bg-paper hover:text-charcoal" aria-label="Hide list" @click="emit('close')">
        <FeatherIcon name="x" class="h-4 w-4" />
      </button>
    </div>

    <div class="space-y-3">
      <div v-for="g in groups" :key="g.tab">
        <p class="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">{{ g.tab }} · {{ g.items.length }}</p>
        <ul class="divide-y divide-line overflow-hidden rounded-md border border-line bg-paper">
          <li v-for="issue in g.items" :key="issue.fieldname">
            <button
              class="flex w-full items-start gap-3 px-3 py-2 text-left transition-colors hover:bg-canvas"
              @click="emit('jump', issue)"
            >
              <FeatherIcon
                :name="issue.kind === 'confirm' ? 'check-square' : issue.kind === 'choose' ? 'list' : 'edit-3'"
                class="mt-0.5 h-4 w-4 shrink-0 text-danger"
              />
              <span class="min-w-0 flex-1">
                <span class="block text-sm font-medium text-charcoal">{{ issue.section || issue.question }}</span>
                <span v-if="issue.section" class="block truncate text-xs text-muted">{{ issue.question }}</span>
                <span class="block text-xs text-danger">{{ issue.message }}</span>
              </span>
              <FeatherIcon name="arrow-right" class="mt-0.5 h-4 w-4 shrink-0 text-muted" />
            </button>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>
