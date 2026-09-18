import { call } from './api'
import type { ProjectSchema } from '@/types/schema'

export function fetchProjectSchema() {
  return call<ProjectSchema>('sirb.sirb_api.meta.get_irb_project_schema')
}
