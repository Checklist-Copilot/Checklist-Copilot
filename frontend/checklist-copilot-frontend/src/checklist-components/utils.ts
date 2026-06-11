export function componentTitle(component: { label?: string; title?: string; id: string }) {
  return component.label ?? component.title ?? component.id
}

export function defaultLabelForType(type: string) {
  switch (type) {
    case 'section':
      return 'New Section'
    case 'textField':
      return 'Untitled field'
    case 'numberField':
    case 'numericField':
      return 'Untitled field'
    case 'checkboxGroup':
    case 'checkboxContainer':
      return 'New Checkbox Group'
    case 'checkbox':
    case 'checkboxItem':
      return 'New checkbox item'
    case 'imageBlock':
    case 'imagesSection':
      return 'New Image Block'
    case 'table':
      return 'New Table'
    default:
      return 'Untitled component'
  }
}

export function formatRange(min?: number | null, max?: number | null) {
  if (min !== null && min !== undefined && max !== null && max !== undefined) {
    return `Allowed range: ${min} to ${max}`
  }

  if (min !== null && min !== undefined) return `Minimum: ${min}`
  if (max !== null && max !== undefined) return `Maximum: ${max}`

  return ''
}
