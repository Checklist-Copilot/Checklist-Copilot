import { useEffect, useState } from 'react'
import { getUserById } from '../api/user'

// Resolves a checklist owner id into the display name shown in checklist metadata.
// If the lookup fails, the UI falls back to the original id so metadata never disappears.
export function useChecklistCreatorName(userId: string | undefined) {
  const [creatorName, setCreatorName] = useState<string | null>(null)

  useEffect(() => {
    if (!userId) {
      setCreatorName(null)
      return
    }

    let isMounted = true
    const resolvedUserId = userId

    async function fetchCreatorName() {
      try {
        const user = await getUserById(resolvedUserId)
        if (isMounted) setCreatorName(user.username)
      } catch {
        if (isMounted) setCreatorName(resolvedUserId)
      }
    }

    void fetchCreatorName()

    return () => {
      isMounted = false
    }
  }, [userId])

  return creatorName ?? userId ?? null
}
