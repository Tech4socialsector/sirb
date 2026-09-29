<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button, FeatherIcon, toast } from 'frappe-ui'
import AppShell from '@/components/layout/AppShell.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import LoadingState from '@/components/common/LoadingState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import DataTable, { type DataTableColumn } from '@/components/common/DataTable.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import OrgUnitTree from '@/components/setup/OrgUnitTree.vue'
import OrgUnitDialog from '@/components/setup/OrgUnitDialog.vue'
import IrbUnitDialog from '@/components/setup/IrbUnitDialog.vue'
import { deleteIrbUnit, deleteOrgUnit, fetchSetupData } from '@/services/setup'
import { ApiError } from '@/services/api'
import { buildOrgIndex } from '@/utils/orgTree'
import { committeeWarning, resolveMembers, setupIssues, type SetupTab } from '@/utils/setupChecks'
import type { IrbUnitRow, OrgUnit, SetupData } from '@/types/setup'

const route = useRoute()
const router = useRouter()

const data = ref<SetupData | null>(null)
const loading = ref(true)
const refreshing = ref(false)
const error = ref<ApiError | null>(null)

async function load() {
  // Only the first load blanks the page; refreshes after a save keep the
  // current view on screen so the admin doesn't lose their place.
  if (data.value) refreshing.value = true
  else loading.value = true
  error.value = null
  try {
    data.value = await fetchSetupData()
  } catch (e) {
    const err = e instanceof ApiError ? e : new ApiError('Failed to load setup data.', 'server')
    if (data.value) toast.error(err.message)
    else error.value = err
  } finally {
    loading.value = false
    refreshing.value = false
  }
}
onMounted(load)

// ---- tabs (kept in ?tab= so a refresh / shared link lands on the same tab)
const TABS: { value: SetupTab; label: string; icon: string }[] = [
  { value: 'organization', label: 'Organization', icon: 'git-branch' },
  { value: 'irb-units', label: 'IRB Units', icon: 'shield' },
]
function tabFromQuery(): SetupTab {
  const t = route.query.tab
  // Old links to the retired Faculty Memberships tab land on IRB Units,
  // where committee faculty are now managed.
  if (t === 'memberships') return 'irb-units'
  return TABS.some((x) => x.value === t) ? (t as SetupTab) : 'organization'
}
const tab = ref<SetupTab>(tabFromQuery())
// `immediate` also rewrites an unknown/retired ?tab= to the tab actually shown.
watch(
  tab,
  (t) => {
    if (route.query.tab !== undefined && route.query.tab !== t) router.replace({ query: { ...route.query, tab: t } })
    else if (route.query.tab === undefined && t !== 'organization') router.replace({ query: { ...route.query, tab: t } })
  },
  { immediate: true },
)
watch(
  () => route.query.tab,
  () => (tab.value = tabFromQuery()),
)

// ---- derived lookups
const units = computed(() => data.value?.units ?? [])
const irbUnits = computed(() => data.value?.irb_units ?? [])
const memberships = computed(() => data.value?.memberships ?? [])
const index = computed(() => buildOrgIndex(units.value))
const membershipByName = computed(() => new Map(memberships.value.map((m) => [m.name, m])))
const irbUnitByAo = computed(() => new Map(irbUnits.value.map((u) => [u.ao_unit, u.name])))
const facultyCountByAo = computed(() => {
  const m = new Map<string, number>()
  for (const f of memberships.value) m.set(f.ao_unit, (m.get(f.ao_unit) || 0) + 1)
  return m
})
const issues = computed(() => (data.value ? setupIssues(data.value, index.value) : []))
const tabCounts = computed<Record<SetupTab, number>>(() => ({
  organization: units.value.length,
  'irb-units': irbUnits.value.length,
}))

const ISSUE_STYLE = {
  danger: { icon: 'alert-octagon', cls: 'text-danger' },
  warning: { icon: 'alert-triangle', cls: 'text-warning' },
  info: { icon: 'info', cls: 'text-info' },
} as const

// ---- Organization tab
const orgSearch = ref('')
const treeRef = ref<InstanceType<typeof OrgUnitTree> | null>(null)
const orgDialog = ref({ open: false, unit: null as OrgUnit | null, parent: null as string | null })

function addUnit(parent: OrgUnit | null = null) {
  orgDialog.value = { open: true, unit: null, parent: parent?.name ?? null }
}
function editUnit(unit: OrgUnit) {
  orgDialog.value = { open: true, unit, parent: null }
}

// ---- IRB Units tab
const irbSearch = ref('')
const irbDialog = ref({ open: false, irbUnit: null as IrbUnitRow | null, aoUnit: null as string | null })

function addIrbUnit(aoUnit: string | null = null) {
  irbDialog.value = { open: true, irbUnit: null, aoUnit }
}
function editIrbUnit(irbUnit: IrbUnitRow) {
  irbDialog.value = { open: true, irbUnit, aoUnit: null }
}

const filteredIrbUnits = computed(() => {
  const term = irbSearch.value.trim().toLowerCase()
  const rows = irbUnits.value.map((u) => {
    const members = resolveMembers(u, membershipByName.value)
    return {
      ...u,
      path: index.value.path(u.ao_unit) || u.ao_name,
      member_list: members,
      member_count: members.length,
      warning: committeeWarning({ members, num_reviewers: u.num_reviewers, mentor_required: !!u.mentor_required }),
    }
  })
  if (!term) return rows
  return rows.filter((r) =>
    [r.ao_name, r.path, ...r.member_list.map((m) => m.faculty_name)].some((v) => v?.toLowerCase().includes(term)),
  )
})
type IrbRow = (typeof filteredIrbUnits.value)[number]

const irbColumns: DataTableColumn[] = [
  { key: 'ao_name', label: 'Unit', sortable: true },
  { key: 'mentor_required', label: 'Mentor', sortable: true },
  { key: 'num_reviewers', label: 'Reviewers', sortable: true },
  { key: 'member_count', label: 'Committee', sortable: true },
  { key: 'project_count', label: 'Projects', sortable: true, align: 'right' },
  { key: 'actions', label: '', align: 'right' },
]

// ---- delete confirmation (shared by all three tabs)
const confirm = ref({ open: false, title: '', message: '', run: async () => {} })

function askDelete(title: string, message: string, action: () => Promise<void>, success: string) {
  confirm.value = {
    open: true,
    title,
    message,
    run: async () => {
      try {
        await action()
        toast.success(success)
        await load()
      } catch (e) {
        toast.error(e instanceof Error ? e.message : 'Delete failed.')
      }
    },
  }
}

function confirmDeleteUnit(u: OrgUnit) {
  askDelete(
    `Delete ${u.ao_name}?`,
    'This permanently removes the unit. It will be refused if it has child units, faculty, students, projects or an IRB Unit.',
    () => deleteOrgUnit(u.name),
    `${u.ao_name} deleted.`,
  )
}
function confirmDeleteIrbUnit(u: IrbUnitRow) {
  askDelete(
    `Delete the IRB Unit for ${u.ao_name}?`,
    'Its committee is removed, and faculty who no longer sit on any committee lose the IRB Reviewer role.',
    () => deleteIrbUnit(u.name),
    `IRB Unit for ${u.ao_name} deleted.`,
  )
}
function onSaved(message: string) {
  toast.success(message)
  load()
}

function goToTab(t: SetupTab) {
  tab.value = t
}
</script>

<template>
  <AppShell>
    <PageHeader
      title="Setup"
      description="Configure the organisation structure and IRB Units (review rules and committee) before a review cycle starts."
    >
      <template #actions>
        <Button variant="outline" icon-left="refresh-cw" :loading="refreshing" :disabled="loading" @click="load">Refresh</Button>
      </template>
    </PageHeader>

    <LoadingState v-if="loading && !data" label="Loading setup…" />
    <ErrorState v-else-if="error" :error="error" @retry="load" />
    <template v-else-if="data">
      <!-- Setup checklist -->
      <div class="mb-5 rounded-xl border border-line bg-paper p-5 shadow-card">
        <div class="flex flex-wrap items-center gap-2" :class="issues.length ? 'mb-3' : ''">
          <FeatherIcon
            :name="issues.some((i) => i.level !== 'info') ? 'clipboard' : 'check-circle'"
            class="h-4 w-4"
            :class="issues.some((i) => i.level !== 'info') ? 'text-warning' : 'text-success'"
          />
          <h2 class="text-sm font-semibold text-charcoal">Setup checklist</h2>
          <span class="text-xs text-muted">
            {{ issues.length ? `${issues.length} item${issues.length === 1 ? '' : 's'} to review` : 'Everything needed for reviewer assignment is in place.' }}
          </span>
        </div>
        <ul v-if="issues.length" class="divide-y divide-line">
          <li v-for="(issue, i) in issues" :key="i" class="flex items-start gap-3 py-2.5">
            <FeatherIcon :name="ISSUE_STYLE[issue.level].icon" class="mt-0.5 h-4 w-4 shrink-0" :class="ISSUE_STYLE[issue.level].cls" />
            <div class="min-w-0 flex-1">
              <p class="text-sm font-medium text-charcoal">{{ issue.title }}</p>
              <p class="text-sm text-muted">{{ issue.detail }}</p>
            </div>
            <button
              v-if="issue.tab !== tab"
              class="shrink-0 text-sm font-medium text-primary hover:underline"
              @click="goToTab(issue.tab)"
            >
              Review
            </button>
          </li>
        </ul>
      </div>

      <div class="rounded-xl border border-line bg-paper shadow-card">
        <div class="flex gap-1 overflow-x-auto overflow-y-hidden border-b border-line px-6">
          <button
            v-for="t in TABS"
            :key="t.value"
            class="relative flex shrink-0 items-center gap-2 px-3 py-2.5 text-sm font-medium transition-colors"
            :class="tab === t.value ? 'text-charcoal' : 'text-muted hover:text-charcoal'"
            @click="tab = t.value"
          >
            <FeatherIcon :name="t.icon" class="h-4 w-4" />
            {{ t.label }}
            <span
              class="rounded-full px-2 py-0.5 text-xs font-semibold"
              :class="tab === t.value ? 'bg-primary text-white' : 'bg-canvas text-muted'"
            >
              {{ tabCounts[t.value] }}
            </span>
            <span v-if="tab === t.value" class="absolute inset-x-0 bottom-0 h-0.5 rounded-full bg-primary" />
          </button>
        </div>

        <div class="p-6">
          <!-- Organization -->
          <template v-if="tab === 'organization'">
            <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
              <input
                v-model="orgSearch"
                type="text"
                placeholder="Search units…"
                class="w-64 rounded-md border border-line bg-canvas px-3 py-1.5 text-sm text-charcoal placeholder:text-muted focus:border-primary focus:outline-none"
              />
              <div class="flex flex-wrap items-center gap-2">
                <template v-if="units.length && !orgSearch">
                  <Button variant="ghost" @click="treeRef?.expandAll()">Expand all</Button>
                  <Button variant="ghost" @click="treeRef?.collapseAll()">Collapse all</Button>
                </template>
                <Button variant="solid" icon-left="plus" @click="addUnit()">Add Unit</Button>
              </div>
            </div>
            <OrgUnitTree
              ref="treeRef"
              :index="index"
              :irb-unit-by-ao="irbUnitByAo"
              :faculty-count-by-ao="facultyCountByAo"
              :search="orgSearch"
              @add-child="addUnit"
              @edit="editUnit"
              @delete="confirmDeleteUnit"
              @setup-irb="(u) => addIrbUnit(u.name)"
            />
          </template>

          <!-- IRB Units -->
          <template v-else>
            <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
              <input
                v-model="irbSearch"
                type="text"
                placeholder="Search units or committee members…"
                class="w-72 rounded-md border border-line bg-canvas px-3 py-1.5 text-sm text-charcoal placeholder:text-muted focus:border-primary focus:outline-none"
              />
              <Button variant="solid" icon-left="plus" :disabled="!units.length" @click="addIrbUnit()">Add IRB Unit</Button>
            </div>
            <DataTable
              :columns="irbColumns"
              :rows="filteredIrbUnits as unknown as Record<string, unknown>[]"
              row-key="name"
              :empty-title="irbSearch ? 'No IRB Units match your search' : 'No IRB Units yet'"
              :empty-description="irbSearch ? undefined : 'An IRB Unit sets the committee and review rules for one Academic Organizational Unit.'"
            >
              <template #cell-ao_name="{ row }">
                <div class="max-w-xs">
                  <button
                    class="truncate text-left font-medium text-charcoal hover:text-primary"
                    @click="editIrbUnit(row as unknown as IrbRow)"
                  >
                    {{ (row as unknown as IrbRow).ao_name }}
                  </button>
                  <p class="truncate text-xs text-muted">{{ (row as unknown as IrbRow).path }}</p>
                </div>
              </template>
              <template #cell-mentor_required="{ value }">
                <span
                  class="rounded-full px-2 py-0.5 text-xs font-medium"
                  :class="value ? 'bg-blue-50 text-info' : 'bg-canvas text-muted'"
                >
                  {{ value ? 'Required' : 'Not required' }}
                </span>
              </template>
              <template #cell-num_reviewers="{ value }">{{ value === '2' ? 'Primary + Secondary' : 'Primary only' }}</template>
              <template #cell-member_count="{ row }">
                <div class="flex items-center gap-2">
                  <span>{{ (row as unknown as IrbRow).member_count }}</span>
                  <FeatherIcon
                    v-if="(row as unknown as IrbRow).warning"
                    name="alert-triangle"
                    class="h-4 w-4"
                    :class="(row as unknown as IrbRow).warning!.level === 'danger' ? 'text-danger' : 'text-warning'"
                    :title="(row as unknown as IrbRow).warning!.message"
                  />
                  <span class="max-w-[16rem] truncate text-xs text-muted">
                    {{ (row as unknown as IrbRow).member_list.map((m) => m.faculty_name).join(', ') }}
                  </span>
                </div>
              </template>
              <template #cell-actions="{ row }">
                <div class="flex items-center justify-end gap-1">
                  <button class="text-sm font-medium text-primary hover:underline" @click="editIrbUnit(row as unknown as IrbRow)">
                    Edit
                  </button>
                  <button
                    class="rounded-md p-1.5 text-muted transition-colors hover:bg-canvas hover:text-danger disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-muted"
                    :disabled="(row as unknown as IrbRow).project_count > 0"
                    :title="(row as unknown as IrbRow).project_count > 0 ? 'Has projects — cannot be deleted' : 'Delete'"
                    @click="confirmDeleteIrbUnit(row as unknown as IrbRow)"
                  >
                    <FeatherIcon name="trash-2" class="h-4 w-4" />
                  </button>
                </div>
              </template>
            </DataTable>
          </template>
        </div>
      </div>

      <OrgUnitDialog
        v-model="orgDialog.open"
        :unit="orgDialog.unit"
        :parent="orgDialog.parent"
        :index="index"
        :ao-types="data.ao_types"
        @saved="onSaved(orgDialog.unit ? 'Unit updated.' : 'Unit added.')"
      />
      <IrbUnitDialog
        v-model="irbDialog.open"
        :irb-unit="irbDialog.irbUnit"
        :ao-unit="irbDialog.aoUnit"
        :index="index"
        :irb-units="irbUnits"
        :memberships="memberships"
        :faculty="data.faculty"
        @saved="onSaved(irbDialog.irbUnit ? 'IRB Unit updated.' : 'IRB Unit added.')"
      />
      <ConfirmDialog
        v-model="confirm.open"
        :title="confirm.title"
        :message="confirm.message"
        :on-confirm="confirm.run"
      />
    </template>
  </AppShell>
</template>
