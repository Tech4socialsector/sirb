<script setup lang="ts">
import { ref } from 'vue'
import { Button, toast } from 'frappe-ui'
import AppShell from '@/components/layout/AppShell.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import UploadDialog from '@/components/uploads/UploadDialog.vue'
import ProgressLog from '@/components/uploads/ProgressLog.vue'
import { useUploader } from '@/composables/useUploader'
import { enqueueFacultyUpload, uploadFile } from '@/services/uploads'

const dialogOpen = ref(false)
const submitting = ref(false)
const { state, start } = useUploader('sirb_faculty_import_progress')

const fields = [
  {
    fieldname: 'ao_unit',
    label: 'Academic Organizational Unit',
    type: 'link' as const,
    doctype: 'Academic Organizational Unit',
    required: true,
  },
]

async function onSubmit({ values, file }: { values: Record<string, string>; file: File }) {
  submitting.value = true
  dialogOpen.value = false
  try {
    const uploaded = await uploadFile(file)
    start()
    const message = await enqueueFacultyUpload({ ao_unit: values.ao_unit, file_url: uploaded.file_url })
    toast.info(message)
  } catch (e) {
    toast.error(e instanceof Error ? e.message : 'Upload failed to start')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <AppShell>
    <PageHeader title="Upload Faculty" description="Select an Academic Organizational Unit and upload a CSV file." />

    <div class="flex flex-col items-center gap-6 rounded-lg border border-gray-200 bg-white py-16">
      <Button variant="solid" size="lg" :loading="submitting" :disabled="state.active && !state.completed" @click="dialogOpen = true">
        Upload File
      </Button>
      <ProgressLog v-if="state.active" :progress="state.progress" :log="state.log" :completed="state.completed" />
    </div>

    <UploadDialog v-model="dialogOpen" title="Upload Faculty List" :fields="fields" @submit="onSubmit" />
  </AppShell>
</template>
