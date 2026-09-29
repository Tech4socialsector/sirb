<script setup lang="ts">
import { ref } from 'vue'
import { Button, FeatherIcon, toast } from 'frappe-ui'
import AppShell from '@/components/layout/AppShell.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import UploadDialog from '@/components/uploads/UploadDialog.vue'
import ProgressLog from '@/components/uploads/ProgressLog.vue'
import { useUploader } from '@/composables/useUploader'
import { enqueueStudentUpload, uploadFile } from '@/services/uploads'
import { downloadStudentSampleSheet } from '@/utils/sampleSheets'

const dialogOpen = ref(false)
const submitting = ref(false)
const { state, start } = useUploader('sirb_student_import_progress')

// The backend importer (sirb.api.import_student_irb_information) is
// header-driven — it accepts however many student-name-N/id-N/email-N
// columns are present on a row, so "individual" vs "group" isn't a
// different upload endpoint or format, just a different number of those
// columns. This tab only changes which sample template/instructions are
// shown; both submit through the same dialog and API call.
type ProjectKind = 'individual' | 'group'
const kind = ref<ProjectKind>('individual')

const fields = [
  { fieldname: 'irb_unit', label: 'IRB Unit', type: 'link' as const, doctype: 'IRB Unit', required: true },
  { fieldname: 'irb_cycle', label: 'IRB Cycle / Year Name', type: 'text' as const, required: true },
]

async function onSubmit({ values, file }: { values: Record<string, string>; file: File }) {
  submitting.value = true
  dialogOpen.value = false
  try {
    const uploaded = await uploadFile(file)
    start()
    const message = await enqueueStudentUpload({
      irb_unit: values.irb_unit,
      irb_cycle: values.irb_cycle,
      file_url: uploaded.file_url,
    })
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
    <PageHeader title="Upload IRB Students" description="Select an IRB Unit and upload a CSV file." />

    <div class="mb-4 inline-flex rounded-md border border-line bg-paper p-1">
      <button
        class="rounded px-3 py-1.5 text-sm font-medium transition-colors"
        :class="kind === 'individual' ? 'bg-primary text-white' : 'text-muted hover:text-charcoal'"
        @click="kind = 'individual'"
      >
        Individual Project
      </button>
      <button
        class="rounded px-3 py-1.5 text-sm font-medium transition-colors"
        :class="kind === 'group' ? 'bg-primary text-white' : 'text-muted hover:text-charcoal'"
        @click="kind = 'group'"
      >
        Group Project
      </button>
    </div>

    <div class="mb-4 flex items-start gap-3 rounded-lg border border-line bg-paper p-4 shadow-card">
      <FeatherIcon name="file-text" class="mt-0.5 h-4 w-4 shrink-0 text-muted" />
      <div class="min-w-0 flex-1">
        <p class="text-sm font-medium text-charcoal">Expected columns</p>
        <p v-if="kind === 'individual'" class="mt-0.5 text-sm text-muted">
          One student per project: <span class="font-medium text-charcoal">Student-name-1</span>,
          <span class="font-medium text-charcoal">student-id-1</span>,
          <span class="font-medium text-charcoal">Student-email-1</span>, plus
          <span class="font-medium text-charcoal">Mentor-name</span> and
          <span class="font-medium text-charcoal">Mentor-email</span>.
        </p>
        <p v-else class="mt-0.5 text-sm text-muted">
          Multiple students sharing one project: repeat the student columns per student —
          <span class="font-medium text-charcoal">Student-name-1/2/3…</span>,
          <span class="font-medium text-charcoal">student-id-1/2/3…</span>,
          <span class="font-medium text-charcoal">Student-email-1/2/3…</span> — on the same row, plus one
          <span class="font-medium text-charcoal">Mentor-name</span> / <span class="font-medium text-charcoal">Mentor-email</span>
          for the group.
        </p>
      </div>
      <Button variant="outline" size="sm" icon-left="download" @click="downloadStudentSampleSheet(kind)">
        Download sample sheet
      </Button>
    </div>

    <div class="flex flex-col items-center gap-6 rounded-lg border border-line bg-paper px-6 shadow-card" :class="state.active ? 'py-8' : 'py-16'">
      <Button variant="solid" size="lg" :loading="submitting" :disabled="state.active && !state.completed" @click="dialogOpen = true">
        Upload File
      </Button>
      <ProgressLog v-if="state.active" :progress="state.progress" :log="state.log" :completed="state.completed" :had-error="state.hadError" />
    </div>

    <UploadDialog v-model="dialogOpen" title="Upload IRB Students File" :fields="fields" @submit="onSubmit" />
  </AppShell>
</template>
