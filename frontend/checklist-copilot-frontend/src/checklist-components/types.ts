export type ComponentType =
  | 'section'
  | 'checkboxGroup'
  | 'checkboxContainer'
  | 'checkbox'
  | 'checkboxItem'
  | 'textField'
  | 'numberField'
  | 'numericField'
  | 'imageBlock'
  | 'imagesSection'
  | 'table'

export interface ChecklistBaseComponent {
  id: string
  humanReadableId?: string | null
  type: ComponentType
  label?: string
  title?: string
  description?: string
}

export interface ChecklistRoot {
  id: 'root' | string
  type: 'root'
  version?: number | string
  title?: string
  children: ChecklistComponent[]
}

export interface SectionComponent extends ChecklistBaseComponent {
  type: 'section'
  collapsed?: boolean
  children: ChecklistComponent[]
}

export interface CheckboxGroupComponent extends ChecklistBaseComponent {
  type: 'checkboxGroup' | 'checkboxContainer'
  items: CheckboxComponent[]
}

export interface CheckboxComponent extends ChecklistBaseComponent {
  type: 'checkbox' | 'checkboxItem'
  checked: boolean
  required?: boolean
}

export interface TextFieldComponent extends ChecklistBaseComponent {
  type: 'textField'
  value: string
  placeholder?: string | null
  required?: boolean
  multiline?: boolean
}

export interface NumberFieldComponent extends ChecklistBaseComponent {
  type: 'numberField' | 'numericField'
  value: number | null
  unit?: string | null
  min?: number | null
  max?: number | null
  required?: boolean
}

export interface ChecklistImage {
  imageId?: string
  id?: string
  type?: 'imageRef'
  url?: string
  label?: string | null
  caption?: string | null
  bucket?: string
  path?: string
  mimeType?: string
}

export interface ImageBlockComponent extends ChecklistBaseComponent {
  type: 'imageBlock' | 'imagesSection'
  images: ChecklistImage[]
  allowUpload?: boolean
}

export type TableColumnType = 'text' | 'number' | 'checkbox' | 'date'
export type TableCellValue = string | number | boolean | null

export interface TableColumn {
  id: string
  label: string
  type?: TableColumnType
  valueType?: TableColumnType
}

export interface TableRow {
  id: string
  cells: Record<string, TableCellValue>
}

export interface TableComponent extends ChecklistBaseComponent {
  type: 'table'
  columns: TableColumn[]
  rows: TableRow[]
}

export type ChecklistComponent =
  | SectionComponent
  | CheckboxGroupComponent
  | CheckboxComponent
  | TextFieldComponent
  | NumberFieldComponent
  | ImageBlockComponent
  | TableComponent
