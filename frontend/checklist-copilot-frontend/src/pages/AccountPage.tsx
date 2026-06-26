import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  FiAlertTriangle,
  FiEdit2,
  FiEye,
  FiEyeOff,
  FiLock,
  FiMail,
  FiSave,
  FiTrash2,
  FiUser,
} from 'react-icons/fi'
import { changePassword, getCurrentUser, updateCurrentUser } from '../api/auth'
import { deleteUser } from '../api/user'
import { ApiError } from '../api/http'
import { removeToken } from '../auth/tokenStorage'
import TopBar from '../components/TopBar'
import { ConfirmationModal } from '../components/ConfirmationModal'
import styles from '../page-styles/AccountPage.module.css'
import type { User } from '../types/user'

function AccountPage() {
  const navigate = useNavigate()
  const [user, setUser] = useState<User | null>(null)
  const [displayName, setDisplayName] = useState('')
  const [email, setEmail] = useState('')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPasswords, setShowPasswords] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [isSavingProfile, setIsSavingProfile] = useState(false)
  const [isSavingPassword, setIsSavingPassword] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false)
  const [profileMessage, setProfileMessage] = useState<string | null>(null)
  const [passwordMessage, setPasswordMessage] = useState<string | null>(null)
  const [dangerMessage, setDangerMessage] = useState<string | null>(null)

  useEffect(() => {
    let isMounted = true

    async function loadUser() {
      try {
        const currentUser = await getCurrentUser()
        if (!isMounted) return
        setUser(currentUser)
        setDisplayName(currentUser.username)
        setEmail(currentUser.email)
      } catch {
        removeToken()
        if (isMounted) navigate('/')
      } finally {
        if (isMounted) setIsLoading(false)
      }
    }

    void loadUser()

    return () => {
      isMounted = false
    }
  }, [navigate])

  const initials = useMemo(() => {
    const source = displayName.trim() || email.trim() || 'User'
    return source
      .split(/\s+/)
      .slice(0, 2)
      .map((part) => part[0])
      .join('')
      .toUpperCase()
  }, [displayName, email])

  function handleLogout() {
    removeToken()
    navigate('/')
  }

  async function handleProfileSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const username = displayName.trim()
    const nextEmail = email.trim()

    if (!username || !nextEmail) {
      setProfileMessage('Display name and email are required.')
      return
    }

    setIsSavingProfile(true)
    setProfileMessage(null)

    try {
      const updatedUser = await updateCurrentUser({ username, email: nextEmail })
      setUser(updatedUser)
      setDisplayName(updatedUser.username)
      setEmail(updatedUser.email)
      setProfileMessage('Profile updated.')
    } catch (error) {
      setProfileMessage(error instanceof ApiError ? error.message : 'Could not update your profile. Please try again.')
    } finally {
      setIsSavingProfile(false)
    }
  }

  async function handlePasswordSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (newPassword !== confirmPassword) {
      setPasswordMessage('New passwords do not match.')
      return
    }

    if (!currentPassword || !newPassword) {
      setPasswordMessage('Fill in your current password and new password.')
      return
    }

    setIsSavingPassword(true)
    setPasswordMessage(null)

    try {
      await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      })
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setPasswordMessage('Password updated.')
    } catch (error) {
      setPasswordMessage(error instanceof ApiError ? error.message : 'Could not update your password. Please try again.')
    } finally {
      setIsSavingPassword(false)
    }
  }

  // Opens the shared destructive confirmation modal for account deletion.
  function handleDeleteAccount() {
    if (!user || isDeleting) return
    setIsDeleteModalOpen(true)
  }

  // Deletes the signed-in account only after the modal confirmation succeeds.
  async function confirmDeleteAccount() {
    if (!user || isDeleting) return

    setIsDeleting(true)
    setDangerMessage(null)

    try {
      await deleteUser(user.id)
      removeToken()
      navigate('/')
    } catch {
      setDangerMessage('Could not delete your account. Please try again.')
    } finally {
      setIsDeleting(false)
      setIsDeleteModalOpen(false)
    }
  }

  if (isLoading) {
    return (
      <main className={styles.page}>
        <p className={styles.message}>Loading account...</p>
      </main>
    )
  }

  if (!user) return null

  return (
    <>
      <TopBar userName={user.username} userEmail={user.email} onLogout={handleLogout} />

      <main className={styles.page}>
        <header className={styles.header}>
          <div>
            <h1 className={styles.title}>My Account</h1>
            <p className={styles.subtitle}>Manage your profile and security settings</p>
          </div>
        </header>

        <section className={styles.stack}>
          <form className={styles.panel} onSubmit={handleProfileSubmit}>
            <div className={styles.identity}>
              <div className={styles.avatar}>{initials}</div>
              <div>
                <h2>{displayName || 'User'}</h2>
                <p>{email}</p>
              </div>
            </div>

            <div className={styles.fieldGrid}>
              <label className={styles.field}>
                <span>
                  <FiUser />
                  Display Name
                </span>
                <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
              </label>

              <label className={styles.field}>
                <span>
                  <FiMail />
                  Email
                </span>
                <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
              </label>
            </div>

            <div className={styles.formFooter}>
              <button className={styles.secondaryButton} type="submit" disabled={isSavingProfile}>
                <FiEdit2 />
                {isSavingProfile ? 'Saving...' : 'Save Profile'}
              </button>
              {profileMessage ? <p className={styles.note}>{profileMessage}</p> : null}
            </div>
          </form>

          <form className={styles.panel} onSubmit={handlePasswordSubmit}>
            <h2 className={styles.panelTitle}>
              <FiLock />
              Change Password
            </h2>

            <label className={styles.field}>
              <span>Current Password</span>
              <div className={styles.passwordInput}>
                <input
                  type={showPasswords ? 'text' : 'password'}
                  value={currentPassword}
                  onChange={(event) => setCurrentPassword(event.target.value)}
                />
                <button type="button" onClick={() => setShowPasswords((prev) => !prev)} aria-label="Toggle password visibility">
                  {showPasswords ? <FiEyeOff /> : <FiEye />}
                </button>
              </div>
            </label>

            <label className={styles.field}>
              <span>New Password</span>
              <div className={styles.passwordInput}>
                <input
                  type={showPasswords ? 'text' : 'password'}
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                />
                <button type="button" onClick={() => setShowPasswords((prev) => !prev)} aria-label="Toggle password visibility">
                  {showPasswords ? <FiEyeOff /> : <FiEye />}
                </button>
              </div>
            </label>

            <label className={styles.field}>
              <span>Confirm New Password</span>
              <div className={styles.passwordInput}>
                <input
                  type={showPasswords ? 'text' : 'password'}
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                />
                <button type="button" onClick={() => setShowPasswords((prev) => !prev)} aria-label="Toggle password visibility">
                  {showPasswords ? <FiEyeOff /> : <FiEye />}
                </button>
              </div>
            </label>

            <div className={styles.formFooter}>
              <button className={styles.primaryButton} type="submit" disabled={isSavingPassword}>
                <FiSave />
                {isSavingPassword ? 'Updating...' : 'Update Password'}
              </button>
              {passwordMessage ? <p className={styles.note}>{passwordMessage}</p> : null}
            </div>
          </form>

          <section className={`${styles.panel} ${styles.dangerPanel}`}>
            <h2 className={styles.dangerTitle}>
              <FiAlertTriangle />
              Danger Zone
            </h2>
            <p className={styles.dangerText}>
              Permanently delete your account and associated data. This action cannot be undone.
            </p>
            <button className={styles.dangerButton} type="button" onClick={handleDeleteAccount} disabled={isDeleting}>
              <FiTrash2 />
              {isDeleting ? 'Deleting...' : 'Delete Account'}
            </button>
            {dangerMessage ? <p className={styles.dangerMessage}>{dangerMessage}</p> : null}
          </section>
        </section>
      </main>

      <ConfirmationModal
        isOpen={isDeleteModalOpen}
        title="Delete your account?"
        message="This removes your profile, checklists, and associated data. You cannot undo this action."
        confirmLabel="Delete account"
        isConfirming={isDeleting}
        onConfirm={confirmDeleteAccount}
        onClose={() => setIsDeleteModalOpen(false)}
      />
    </>
  )
}

export default AccountPage
