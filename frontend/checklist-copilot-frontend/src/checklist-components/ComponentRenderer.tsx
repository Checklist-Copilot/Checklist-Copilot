import { CheckboxGroupRenderer } from './CheckboxGroupRenderer'
import { CheckboxRenderer } from './CheckboxRenderer'
import { ImageBlockRenderer } from './ImageBlockRenderer'
import { NumberFieldRenderer } from './NumberFieldRenderer'
import { SectionRenderer } from './SectionRenderer'
import { TableRenderer } from './TableRenderer'
import { TextFieldRenderer } from './TextFieldRenderer'
import type { ChecklistComponent } from './types'

type ComponentRendererProps = {
  component: ChecklistComponent
  index?: number
}

export function ComponentRenderer({ component, index }: ComponentRendererProps) {
  switch (component.type) {
    case 'section':
      return <SectionRenderer section={component} index={index} />
    case 'checkboxGroup':
    case 'checkboxContainer':
      return <CheckboxGroupRenderer component={component} />
    case 'checkbox':
    case 'checkboxItem':
      return <CheckboxRenderer component={component} />
    case 'textField':
      return <TextFieldRenderer component={component} />
    case 'numberField':
    case 'numericField':
      return <NumberFieldRenderer component={component} />
    case 'imageBlock':
    case 'imagesSection':
      return <ImageBlockRenderer component={component} />
    case 'table':
      return <TableRenderer component={component} />
    default:
      return null
  }
}
