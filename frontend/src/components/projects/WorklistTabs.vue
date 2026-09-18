<script setup lang="ts">
import { TabButtons } from 'frappe-ui'
import { computed } from 'vue'
import type { WorklistBucket } from '@/services/projects'

const modelValue = defineModel<WorklistBucket>({ required: true })

const buttons = [
  { label: 'Pending', value: 'pending' },
  { label: 'In Progress', value: 'unapproved' },
  { label: 'Approved', value: 'approved' },
]

const value = computed({
  get: () => modelValue.value,
  set: (v: string | number | boolean | undefined) => {
    modelValue.value = v as WorklistBucket
  },
})
</script>

<template>
  <TabButtons :buttons="buttons" v-model="value" />
</template>
