export interface SchemaField {
  fieldname: string
  fieldtype: string
  label: string | null
  options: string | null
  reqd: number
  read_only: number
  depends_on: string | null
  mandatory_depends_on: string | null
  read_only_depends_on: string | null
  description: string | null
  permlevel: number
  default: string | null
}

export interface ProjectSchema {
  fields: SchemaField[]
  field_order: string[]
}

export interface SchemaTab {
  fieldname: string
  label: string
  sections: SchemaSection[]
}

export interface SchemaSection {
  fieldname: string
  label: string | null
  columns: SchemaField[][]
}
