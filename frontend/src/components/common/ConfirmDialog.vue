<script setup lang="ts">
import { ref } from 'vue'
import { Button, Dialog } from 'frappe-ui'

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    title: string
    message: string
    confirmLabel?: string
    /** Runs on confirm; the dialog stays open (with a spinner) until it
     * settles and closes only on success, so a failed delete can't be
     * mistaken for a successful one. */
    onConfirm: () => Promise<void>
  }>(),
  { confirmLabel: 'Delete' },
)

const emit = defineEmits<{ 'update:modelValue': [boolean] }>()
const busy = ref(false)

async function confirm() {
  if (busy.value) return
  busy.value = true
  try {
    await props.onConfirm()
    emit('update:modelValue', false)
  } catch {
    // The caller already surfaced the error; keep the dialog open.
  } finally {
    busy.value = false
  }
}

function setOpen(v: boolean) {
  if (!busy.value) emit('update:modelValue', v)
}
</script>

<template>
  <Dialog :model-value="modelValue" :options="{ title, size: 'md' }" @update:model-value="setOpen">
    <template #body-content>
      <p class="text-sm text-muted">{{ message }}</p>
    </template>
    <template #actions>
      <div class="flex justify-end gap-2">
        <Button variant="outline" :disabled="busy" @click="setOpen(false)">Cancel</Button>
        <Button variant="solid" theme="red" :loading="busy" @click="confirm">{{ confirmLabel }}</Button>
      </div>
    </template>
  </Dialog>
</template>
