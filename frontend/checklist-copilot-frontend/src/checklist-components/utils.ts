export function componentTitle(component: { label?: string; title?: string; id: string }) {
  return component.label ?? component.title ?? component.id
}

export function formatRange(min?: number | null, max?: number | null) {
  if (min !== null && min !== undefined && max !== null && max !== undefined) {
    return `Allowed range: ${min} to ${max}`
  }

  if (min !== null && min !== undefined) return `Minimum: ${min}`
  if (max !== null && max !== undefined) return `Maximum: ${max}`

  return ''
}
