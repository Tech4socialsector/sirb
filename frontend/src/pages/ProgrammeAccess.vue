<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Button, FeatherIcon, toast } from 'frappe-ui'
import AppShell from '@/components/layout/AppShell.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import LoadingState from '@/components/common/LoadingState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import DataTable, { type DataTableColumn } from '@/components/common/DataTable.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import ProgrammeAccessDialog from '@/components/admin/ProgrammeAccessDialog.vue'
import { ApiError } from '@/services/api'
import {
  deleteProgrammeAccess,
  fetchProgrammeAccess,
  type ProgrammeAccessData,
  type ProgrammeAccessRecord,
} from '@/services/programmeAccess'

const data = ref<ProgrammeAccessData | null>(null)
const loading = ref(true)
const refreshing = ref(false)
const error = ref<ApiError | null>(null)

async function load() {
  // Refreshes after a save keep the table on screen.
  if (data.value) refreshing.value = true
  else loading.value = true
  error.value = null
  try {
    data.value = await fetchProgrammeAccess()
  } catch (e) {
    const err = e instanceof ApiError ? e : new ApiError('Failed to load programme access.', 'server')
    if (data.value) toast.error(err.message)
    else error.value = err
  } finally {
    loading.value = false
    refreshing.value = false
  }
}
onMounted(load)

const search = ref('')
const filtered = computed(() => {
  const rows = data.value?.records ?? []
  const term = search.value.trim().toLowerCase()
  if (!term) return rows
  return rows.filter((r) =>
    [r.user, r.full_name, ...r.programmes.map((p) => p.programme_name)].some((v) => v?.toLowerCase().includes(term)),
  )
})

const columns: DataTableColumn[] = [
  { key: 'full_name', label: 'User', sortable: true },
  { key: 'access_level', label: 'Access', sortable: true },
  { key: 'programmes', label: 'Programmes' },
  { key: 'actions', label: '', align: 'right' },
]
const asRecord = (r: Record<string, unknown>) => r as unknown as ProgrammeAccessRecord

const dialog = ref({ open: false, record: null as ProgrammeAccessRecord | null })
function add() {
  dialog.value = { open: true, record: null }
}
function edit(record: ProgrammeAccessRecord) {
  dialog.value = { open: true, record }
}
function onSaved() {
  toast.success(dialog.value.record ? 'Programme access updated.' : 'Programme access granted.')
  load()
}

const confirm = ref({ open: false, title: '', message: '', run: async () => {} })
function askRemove(record: ProgrammeAccessRecord) {
  const who = record.full_name || record.user
  confirm.value = {
    open: true,
    title: `Remove access for ${who}?`,
    message: 'They lose their programme role and can no longer open the Admin Console or its projects.',
    run: async () => {
      try {
        await deleteProgrammeAccess(record.user)
        toast.success(`Access removed for ${who}.`)
        await load()
      } catch (e) {
        toast.error(e instanceof Error ? e.message : 'Could not remove access.')
        throw e
      }
    },
  }
}
</script>

<template>
  <AppShell>
    <PageHeader
      title="Programme Access"
      description="Give users an Admin Console limited to the programmes you choose — read only, or read & write."
    >
      <template #actions>
        <Button variant="outline" icon-left="refresh-cw" :loading="refreshing" :disabled="loading" @click="load">Refresh</Button>
        <Button variant="solid" icon-left="plus" :disabled="!data" @click="add">Grant Access</Button>
      </template>
    </PageHeader>

    <LoadingState v-if="loading && !data" label="Loading programme access…" />
    <ErrorState v-else-if="error" :error="error" @retry="load" />
    <div v-else-if="data" class="rounded-xl border border-line bg-paper p-6 shadow-card">
      <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
        <input
          v-model="search"
          type="text"
          placeholder="Search users or programmes…"
          class="w-72 rounded-md border border-line bg-canvas px-3 py-1.5 text-sm text-charcoal placeholder:text-muted focus:border-primary focus:outline-none"
        />
        <span class="text-sm text-muted">{{ data.records.length }} user{{ data.records.length === 1 ? '' : 's' }} with access</span>
      </div>

      <DataTable
        :columns="columns"
        :rows="filtered as unknown as Record<string, unknown>[]"
        row-key="user"
        :page-size="20"
        :empty-title="search ? 'No users match your search' : 'No one has programme access yet'"
        :empty-description="search ? undefined : 'Grant access to let a user view the Admin Console for selected programmes.'"
      >
        <template #cell-full_name="{ row }">
          <div class="max-w-xs">
            <button class="truncate text-left font-medium text-charcoal hover:text-primary" @click="edit(asRecord(row))">
              {{ asRecord(row).full_name || asRecord(row).user }}
            </button>
            <p class="truncate text-xs text-muted">{{ asRecord(row).user }}</p>
            <div class="mt-1 flex flex-wrap gap-1">
              <span v-if="!asRecord(row).enabled" class="rounded-full bg-canvas px-2 py-0.5 text-[11px] font-medium text-muted">
                User disabled
              </span>
              <span
                v-if="!asRecord(row).has_role"
                class="rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-warning"
                title="The role for this access level was removed from this user. Open and save to restore it."
              >
                Role missing — save to restore
              </span>
            </div>
          </div>
        </template>
        <template #cell-access_level="{ value }">
          <span
            class="whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium"
            :class="value === 'Read & Write' ? 'bg-amber-50 text-warning' : 'bg-canvas text-muted'"
          >
            {{ value }}
          </span>
        </template>
        <template #cell-programmes="{ row }">
          <div class="flex max-w-xl flex-wrap gap-1">
            <span
              v-for="p in asRecord(row).programmes"
              :key="p.irb_unit"
              class="rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-info"
            >
              {{ p.programme_name }}
            </span>
            <span v-if="!asRecord(row).programmes.length" class="text-xs text-muted">None — sees no data</span>
          </div>
        </template>
        <template #cell-actions="{ row }">
          <div class="flex items-center justify-end gap-1">
            <button class="text-sm font-medium text-primary hover:underline" @click="edit(asRecord(row))">Edit</button>
            <button
              class="rounded-md p-1.5 text-muted transition-colors hover:bg-canvas hover:text-danger"
              title="Remove access"
              @click="askRemove(asRecord(row))"
            >
              <FeatherIcon name="trash-2" class="h-4 w-4" />
            </button>
          </div>
        </template>
      </DataTable>

      <ProgrammeAccessDialog v-model="dialog.open" :record="dialog.record" :programmes="data.programmes" @saved="onSaved" />
      <ConfirmDialog
        v-model="confirm.open"
        :title="confirm.title"
        :message="confirm.message"
        confirm-label="Remove"
        :on-confirm="confirm.run"
      />
    </div>
  </AppShell>
</template>
