<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Tabs } from 'frappe-ui'
import QuestionnaireSection from './QuestionnaireSection.vue'
import { useProjectSchema } from '@/composables/useProjectSchema'
import type { IrbProjectDoc } from '@/types/project'

const props = defineProps<{
  doc: IrbProjectDoc
  linkTitles?: Record<string, string>
  disabled: boolean
}>()

const emit = defineEmits<{ update: [fieldname: string, value: unknown] }>()

const docRef = computed(() => props.doc)
const { tabs, loading, load, isFieldVisible, isFieldMandatory, isTabVisible } = useProjectSchema(docRef)

load()

const visibleTabs = computed(() =>
  tabs.value.filter((t) => t.fieldname !== '__default__' && isTabVisible(t)),
)

const tabItems = computed(() => visibleTabs.value.map((t) => ({ label: t.label })))
const activeTabIndex = ref(0)

watch(visibleTabs, (val) => {
  if (activeTabIndex.value >= val.length) activeTabIndex.value = 0
})
</script>

<template>
  <div v-if="!loading && visibleTabs.length">
    <Tabs v-model="activeTabIndex" :tabs="tabItems">
      <template #tab-panel="{ tab }">
        <div class="mt-4 space-y-4">
          <QuestionnaireSection
            v-for="section in visibleTabs.find((t) => t.label === tab.label)?.sections || []"
            :key="section.fieldname"
            :section="section"
            :all-fields="tabs.flatMap((t) => t.sections.flatMap((s) => s.columns.flat()))"
            :doc="doc"
            :link-titles="linkTitles"
            :disabled="disabled"
            :is-field-visible="isFieldVisible"
            :is-field-mandatory="isFieldMandatory"
            @update="(fn, v) => emit('update', fn, v)"
          />
        </div>
      </template>
    </Tabs>
  </div>
</template>
