<script setup lang="ts">
import { ref } from 'vue'
import { Button, FeatherIcon, toast } from 'frappe-ui'
import AppShell from '@/components/layout/AppShell.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import UploadDialog from '@/components/uploads/UploadDialog.vue'
import ProgressLog from '@/components/uploads/ProgressLog.vue'
import { useUploader } from '@/composables/useUploader'
import { enqueueFacultyUpload, uploadFile } from '@/services/uploads'
import { downloadFacultySampleSheet } from '@/utils/sampleSheets'

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

    <div class="mb-4 flex items-start gap-3 rounded-lg border border-line bg-paper p-4 shadow-card">
      <FeatherIcon name="file-text" class="mt-0.5 h-4 w-4 shrink-0 text-muted" />
      <div class="min-w-0 flex-1">
        <p class="text-sm font-medium text-charcoal">Expected columns</p>
        <p class="mt-0.5 text-sm text-muted">
          Your CSV needs a <span class="font-medium text-charcoal">Faculty name</span> column and a
          <span class="font-medium text-charcoal">Faculty's email ID</span> column.
        </p>
      </div>
      <Button variant="outline" size="sm" icon-left="download" @click="downloadFacultySampleSheet">
        Download sample sheet
      </Button>
    </div>

    <div class="flex flex-col items-center gap-6 rounded-lg border border-line bg-paper px-6 shadow-card" :class="state.active ? 'py-8' : 'py-16'">
      <Button variant="solid" size="lg" :loading="submitting" :disabled="state.active && !state.completed" @click="dialogOpen = true">
        Upload File
      </Button>
      <ProgressLog v-if="state.active" :progress="state.progress" :log="state.log" :completed="state.completed" :had-error="state.hadError" />
    </div>

    <UploadDialog v-model="dialogOpen" title="Upload Faculty List" :fields="fields" @submit="onSubmit" />
  </AppShell>
</template>
