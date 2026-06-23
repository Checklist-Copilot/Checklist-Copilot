import type { ChecklistComponent, ChecklistImage, ChecklistRoot } from './types'

export type ImageReferenceRemoval = {
  componentId: string
  images: ChecklistImage[]
}

export function updateComponentInRoot(
  root: ChecklistRoot,
  componentId: string,
  patch: Record<string, unknown>,
): ChecklistRoot {
  return {
    ...root,
    children: root.children.map((component) => updateComponent(component, componentId, patch)),
  }
}

function updateComponent(
  component: ChecklistComponent,
  componentId: string,
  patch: Record<string, unknown>,
): ChecklistComponent {
  if (component.id === componentId) {
    return { ...component, ...patch } as ChecklistComponent
  }

  if (component.type === 'section') {
    return {
      ...component,
      children: component.children.map((child) => updateComponent(child, componentId, patch)),
    }
  }

  if (component.type === 'checkboxGroup' || component.type === 'checkboxContainer') {
    return {
      ...component,
      items: component.items.map((item) =>
        item.id === componentId ? { ...item, ...patch } : item,
      ),
    }
  }

  return component
}

export function addComponentToRoot(
  root: ChecklistRoot,
  targetContainerId: string,
  newComponent: ChecklistComponent,
): ChecklistRoot {
  if (targetContainerId === root.id || targetContainerId === 'root') {
    return { ...root, children: [...root.children, newComponent] }
  }

  return {
    ...root,
    children: root.children.map((component) => addComponentToContainer(component, targetContainerId, newComponent)),
  }
}

function addComponentToContainer(
  component: ChecklistComponent,
  targetContainerId: string,
  newComponent: ChecklistComponent,
): ChecklistComponent {
  if (component.type === 'section') {
    if (component.id === targetContainerId) {
      return { ...component, children: [...component.children, newComponent] }
    }

    return {
      ...component,
      children: component.children.map((child) => addComponentToContainer(child, targetContainerId, newComponent)),
    }
  }

  if (component.type === 'checkboxGroup' || component.type === 'checkboxContainer') {
    if (
      component.id === targetContainerId &&
      (newComponent.type === 'checkbox' || newComponent.type === 'checkboxItem')
    ) {
      return { ...component, items: [...component.items, newComponent] }
    }
  }

  return component
}

export function deleteComponentFromRoot(root: ChecklistRoot, componentId: string): ChecklistRoot {
  function removeFromComponent(component: ChecklistComponent): ChecklistComponent {
    if (component.type === 'section') {
      return {
        ...component,
        children: component.children
          .filter((child) => child.id !== componentId)
          .map(removeFromComponent),
      }
    }

    if (component.type === 'checkboxGroup' || component.type === 'checkboxContainer') {
      return {
        ...component,
        items: component.items.filter((item) => item.id !== componentId),
      }
    }

    return component
  }

  return {
    ...root,
    children: root.children
      .filter((component) => component.id !== componentId)
      .map(removeFromComponent),
  }
}

export function removeImageFileReferencesFromRoot(
  root: ChecklistRoot,
  fileId: string,
): { root: ChecklistRoot; removals: ImageReferenceRemoval[] } {
  const removals: ImageReferenceRemoval[] = []

  function removeFromComponent(component: ChecklistComponent): ChecklistComponent {
    if (component.type === 'imageBlock' || component.type === 'imagesSection') {
      const images = component.images.filter((image) => image.imageId !== fileId && image.id !== fileId)

      if (images.length !== component.images.length) {
        removals.push({ componentId: component.id, images })
        return { ...component, images }
      }
    }

    if (component.type === 'section') {
      return {
        ...component,
        children: component.children.map(removeFromComponent),
      }
    }

    return component
  }

  return {
    root: {
      ...root,
      children: root.children.map(removeFromComponent),
    },
    removals,
  }
}
