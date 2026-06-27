import { CheckboxGroupRenderer } from './CheckboxGroupRenderer'
import { CheckboxRenderer } from './CheckboxRenderer'
import { ImageBlockRenderer } from './ImageBlockRenderer'
import { NumberFieldRenderer } from './NumberFieldRenderer'
import { SectionRenderer } from './SectionRenderer'
import { TableRenderer } from './TableRenderer'
import { TextFieldRenderer } from './TextFieldRenderer'
import type { ChecklistOperation } from '../api/checklist'
import type { ChecklistComponent } from './types'

type ComponentRendererProps = {
  component: ChecklistComponent
  index?: number
  checklistId?: string
  isEditMode?: boolean
  onComponentUpdate?: (componentId: string, patch: Record<string, unknown>, operation?: ChecklistOperation) => void
  onDeleteComponent?: (componentId: string) => void
  focusedComponentId?: string
  onFocusComponent?: (componentId: string) => void
}

// Routes a checklist component to its specialized renderer while keeping shared edit handlers wired through the tree.
export function ComponentRenderer({
  component,
  index,
  checklistId,
  isEditMode = false,
  onComponentUpdate,
  onDeleteComponent,
  focusedComponentId,
  onFocusComponent,
}: ComponentRendererProps) {
  switch (component.type) {
    case 'section':
      return (
        <SectionRenderer
          section={component}
          index={index}
          checklistId={checklistId}
          isEditMode={isEditMode}
          onComponentUpdate={onComponentUpdate}
          onDeleteComponent={onDeleteComponent}
          focusedComponentId={focusedComponentId}
          onFocusComponent={onFocusComponent}
        />
      )
    case 'checkboxGroup':
    case 'checkboxContainer':
      return (
        <CheckboxGroupRenderer
          component={component}
          isEditMode={isEditMode}
          onComponentUpdate={onComponentUpdate}
          onDeleteComponent={onDeleteComponent}
          focusedComponentId={focusedComponentId}
          onFocusComponent={onFocusComponent}
        />
      )
    case 'checkbox':
    case 'checkboxItem':
      return <CheckboxRenderer component={component} isEditMode={isEditMode} onComponentUpdate={onComponentUpdate} />
    case 'textField':
      return <TextFieldRenderer component={component} isEditMode={isEditMode} onComponentUpdate={onComponentUpdate} />
    case 'numberField':
    case 'numericField':
      return <NumberFieldRenderer component={component} isEditMode={isEditMode} onComponentUpdate={onComponentUpdate} />
    case 'imageBlock':
    case 'imagesSection':
      return (
        <ImageBlockRenderer
          component={component}
          checklistId={checklistId}
          isEditMode={isEditMode}
          onComponentUpdate={onComponentUpdate}
        />
      )
    case 'table':
      return <TableRenderer component={component} isEditMode={isEditMode} onComponentUpdate={onComponentUpdate} />
    default:
      return null
  }
}
