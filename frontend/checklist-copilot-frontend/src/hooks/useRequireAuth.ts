import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getCurrentUser } from '../api/auth'
import { removeToken } from '../auth/tokenStorage'

export function useRequireAuth() {
  const navigate = useNavigate()
  const [isCheckingAuth, setIsCheckingAuth] = useState(true)
  const [isAuthorized, setIsAuthorized] = useState(false)

  useEffect(() => {
    let isMounted = true

    async function validateAuth() {
      try {
        await getCurrentUser()
        if (isMounted) {
          setIsAuthorized(true)
        }
      } catch {
        removeToken()
        if (isMounted) {
          setIsAuthorized(false)
          navigate('/')
        }
      } finally {
        if (isMounted) {
          setIsCheckingAuth(false)
        }
      }
    }

    void validateAuth()

    return () => {
      isMounted = false
    }
  }, [navigate])

  return { isCheckingAuth, isAuthorized }
}
