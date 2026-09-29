<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { Tabs } from 'frappe-ui'
import QuestionnaireSection from './QuestionnaireSection.vue'
import { useProjectSchema } from '@/composables/useProjectSchema'
import type { IrbProjectDoc } from '@/types/project'

const props = defineProps<{
  doc: IrbProjectDoc
  linkTitles?: Record<string, string>
  disabled: boolean
  issueMessages?: Map<string, string>
}>()

const emit = defineEmits<{ update: [fieldname: string, value: unknown] }>()

const docRef = computed(() => props.doc)
const { tabs, loading, load, isFieldVisible, isFieldMandatory, isSectionVisible, isTabVisible } = useProjectSchema(docRef)

load()

const visibleTabs = computed(() =>
  tabs.value.filter((t) => t.fieldname !== '__default__' && isTabVisible(t)),
)

const tabItems = computed(() => visibleTabs.value.map((t) => ({ label: t.label })))
const activeTabIndex = ref(0)

watch(visibleTabs, (val) => {
  if (activeTabIndex.value >= val.length) activeTabIndex.value = 0
})

/** Switch to the tab holding `fieldname`, scroll it into view and focus
 * its input. Returns false if the field isn't in any visible tab. */
async function focusField(fieldname: string): Promise<boolean> {
  const index = visibleTabs.value.findIndex((t) =>
    t.sections.some((s) => isSectionVisible(s) && s.columns.some((c) => c.some((f) => f.fieldname === fieldname))),
  )
  if (index === -1) return false
  activeTabIndex.value = index
  // The tab panel mounts on the next render; give it two ticks + a frame.
  await nextTick()
  await nextTick()
  await new Promise((r) => requestAnimationFrame(() => r(null)))
  const el = document.getElementById(`field-${fieldname}`)
  if (!el) return false
  el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  el.querySelector<HTMLElement>('textarea, input, button[role="combobox"], [data-slot="trigger"]')?.focus({ preventScroll: true })
  return true
}

defineExpose({ focusField })
</script>

<template>
  <div v-if="!loading && visibleTabs.length">
    <Tabs v-model="activeTabIndex" :tabs="tabItems">
      <template #tab-panel="{ tab }">
        <div class="mt-4 space-y-4">
          <QuestionnaireSection
            v-for="section in (visibleTabs.find((t) => t.label === tab.label)?.sections || []).filter(isSectionVisible)"
            :key="section.fieldname"
            :section="section"
            :all-fields="tabs.flatMap((t) => t.sections.flatMap((s) => s.columns.flat()))"
            :doc="doc"
            :link-titles="linkTitles"
            :disabled="disabled"
            :is-field-visible="isFieldVisible"
            :is-field-mandatory="isFieldMandatory"
            :issue-messages="issueMessages"
            @update="(fn, v) => emit('update', fn, v)"
          />
        </div>
      </template>
    </Tabs>
  </div>
</template>
