import { useEffect, useState } from 'react'
import { listChecklists } from '../../api/checklist'
import { getUserById } from '../../api/user'
import type { ChecklistSummary } from '../../types/checklist'

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
        const owners = await Promise.all(
          ownerIds.map(async (ownerId) => {
            const user = await getUserById(ownerId)
            return [ownerId, user.username] as const
          }),
        )

        if (isMounted) {
          setChecklists(response.checklists)
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
