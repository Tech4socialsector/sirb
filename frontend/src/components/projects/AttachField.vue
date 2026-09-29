<script setup lang="ts">
import { computed, ref } from 'vue'
import { Button, FeatherIcon, FormLabel, toast } from 'frappe-ui'
import { uploadFile } from '@/services/uploads'

const props = defineProps<{
  label?: string
  description?: string
  modelValue: unknown
  required?: boolean
  disabled?: boolean
  /** Document the file is attached to — required to upload. */
  doctype: string
  docname?: string
  fieldname: string
}>()

const emit = defineEmits<{ 'update:modelValue': [string | null] }>()

const input = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
const error = ref('')

const fileUrl = computed(() => (typeof props.modelValue === 'string' && props.modelValue.trim()) || '')
const fileName = computed(() => {
  if (!fileUrl.value) return ''
  const last = fileUrl.value.split('?')[0].split('/').pop() || fileUrl.value
  try {
    return decodeURIComponent(last)
  } catch {
    return last
  }
})

function pick() {
  if (props.disabled || uploading.value) return
  error.value = ''
  input.value?.click()
}

async function onPicked(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  // Reset so choosing the same file again still fires `change`.
  target.value = ''
  if (!file) return
  if (!props.docname) {
    error.value = 'Save the project once before attaching files.'
    return
  }
  if (file.size === 0) {
    error.value = 'That file is empty. Please choose another file.'
    return
  }
  uploading.value = true
  try {
    const uploaded = await uploadFile(file, { doctype: props.doctype, docname: props.docname, fieldname: props.fieldname })
    emit('update:modelValue', uploaded.file_url)
    toast.success(`${file.name} uploaded. Remember to save your changes.`)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'The file could not be uploaded. Please try again.'
  } finally {
    uploading.value = false
  }
}

function remove() {
  if (props.disabled || uploading.value) return
  error.value = ''
  emit('update:modelValue', null)
}
</script>

<template>
  <div class="space-y-1.5">
    <FormLabel v-if="label" :label="label" :required="required" />

    <div v-if="fileUrl" class="flex flex-wrap items-center gap-2 rounded-md border border-line bg-canvas px-3 py-2">
      <FeatherIcon name="paperclip" class="h-4 w-4 shrink-0 text-muted" />
      <a
        :href="fileUrl"
        target="_blank"
        rel="noopener"
        class="min-w-0 flex-1 truncate text-sm font-medium text-primary hover:underline"
        :title="fileName"
      >
        {{ fileName }}
      </a>
      <template v-if="!disabled">
        <Button size="sm" variant="ghost" :loading="uploading" @click="pick">Replace</Button>
        <Button size="sm" variant="ghost" theme="red" :disabled="uploading" @click="remove">Remove</Button>
      </template>
    </div>
    <div v-else-if="disabled" class="rounded-md border border-dashed border-line px-3 py-2 text-sm text-muted">
      No file uploaded
    </div>
    <div v-else>
      <Button variant="subtle" icon-left="upload" :loading="uploading" @click="pick">
        {{ uploading ? 'Uploading…' : 'Attach' }}
      </Button>
    </div>

    <input ref="input" type="file" class="hidden" :disabled="disabled" @change="onPicked" />
    <p v-if="description" class="text-xs text-muted">{{ description }}</p>
    <p v-if="error" class="text-xs font-medium text-danger">{{ error }}</p>
  </div>
</template>
