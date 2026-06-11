import { useEffect, useState } from 'react'
import { listChecklists } from '../../api/checklist'
import { listChecklistFiles } from '../../api/files'
import { getUserById } from '../../api/user'
import type { ChecklistSummary } from '../../types/checklist'

async function hydrateChecklistFileCounts(checklists: ChecklistSummary[]) {
  return Promise.all(
    checklists.map(async (checklist) => {
      try {
        const response = await listChecklistFiles(checklist.id)
        const pdfCount = response.files.filter((file) => file.file_type === 'pdf').length
        const imageCount = response.files.filter((file) => file.file_type === 'image').length

        return {
          ...checklist,
          file_count: response.files.length,
          pdf_count: pdfCount,
          image_count: imageCount,
        }
      } catch {
        return {
          ...checklist,
          file_count: checklist.file_count ?? 0,
          pdf_count: checklist.pdf_count ?? 0,
          image_count: checklist.image_count ?? 0,
        }
      }
    }),
  )
}

export function useHomeChecklists(isAuthorized: boolean) {
  const [checklists, setChecklists] = useState<ChecklistSummary[]>([])
  const [ownerNames, setOwnerNames] = useState<Record<string, string>>({})
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    if (!isAuthorized) return

    let isMounted = true

    async function fetchChecklists() {
      setIsLoading(true)
      setErrorMessage(null)

      try {
        const response = await listChecklists()
        const ownerIds = Array.from(new Set(response.checklists.map((checklist) => checklist.user_id)))
        const [checklistsWithFileCounts, owners] = await Promise.all([
          hydrateChecklistFileCounts(response.checklists),
          Promise.all(ownerIds.map(async (ownerId) => {
            const user = await getUserById(ownerId)
            return [ownerId, user.username] as const
          })),
        ])

        if (isMounted) {
          setChecklists(checklistsWithFileCounts)
          setOwnerNames(Object.fromEntries(owners))
        }
      } catch {
        if (isMounted) setErrorMessage('Could not load checklists.')
      } finally {
        if (isMounted) setIsLoading(false)
      }
    }

    void fetchChecklists()

    return () => {
      isMounted = false
    }
  }, [isAuthorized])

  return { checklists, ownerNames, isLoading, errorMessage, setErrorMessage }
}
