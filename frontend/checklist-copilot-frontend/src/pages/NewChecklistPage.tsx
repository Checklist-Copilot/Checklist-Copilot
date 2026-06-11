import { type ChangeEvent, type FormEvent, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FiArrowLeft, FiFileText, FiUploadCloud, FiX } from 'react-icons/fi'
import TopBar from '../components/TopBar'
import { removeToken } from '../auth/tokenStorage'
import { useRequireAuth } from '../hooks/useRequireAuth'
import { createChecklist } from '../api/checklist'
import { uploadChecklistPdf } from '../api/files'
import styles from '../pages-styles/NewChecklistPage.module.css'

const emptyChecklistTree = {
  id: 'root',
  type: 'root',
  children: [],
}

function formatFileSize(bytes: number) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function getErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : 'Request failed.'
}

function NewChecklistPage() {
  const navigate = useNavigate()
  const { isCheckingAuth, isAuthorized } = useRequireAuth()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [pdfFiles, setPdfFiles] = useState<File[]>([])
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [createdChecklistId, setCreatedChecklistId] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [progressMessage, setProgressMessage] = useState('')
  const [hasSubmitted, setHasSubmitted] = useState(false)

  const titleError = hasSubmitted && !title.trim() ? 'Checklist title is required.' : ''
  const descriptionError = hasSubmitted && !description.trim() ? 'Checklist description is required.' : ''
  const totalUploadSize = useMemo(() => pdfFiles.reduce((sum, file) => sum + file.size, 0), [pdfFiles])

  function handleLogout() {
    removeToken()
    navigate('/')
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const incomingFiles = Array.from(event.target.files ?? [])
    const acceptedFiles = incomingFiles.filter(
      (file) => file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf'),
    )
    const rejectedCount = incomingFiles.length - acceptedFiles.length

    if (rejectedCount > 0) {
      setErrorMessage('Only PDF files can be uploaded as checklist context.')
    } else {
      setErrorMessage(null)
    }

    setPdfFiles((currentFiles) => [...currentFiles, ...acceptedFiles])
    event.target.value = ''
  }

  function removePdf(indexToRemove: number) {
    setPdfFiles((currentFiles) => currentFiles.filter((_, index) => index !== indexToRemove))
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setHasSubmitted(true)
    setErrorMessage(null)
    setCreatedChecklistId(null)

    const trimmedTitle = title.trim()
    const trimmedDescription = description.trim()

    if (!trimmedTitle || !trimmedDescription) return

    setIsSubmitting(true)
    setProgressMessage('Creating checklist...')

    let newChecklistId: string | null = null

    try {
      const createdChecklist = await createChecklist({
        title: trimmedTitle,
        description: trimmedDescription,
        checklist: emptyChecklistTree,
      })
      newChecklistId = createdChecklist.id
      setCreatedChecklistId(createdChecklist.id)

      for (const [index, file] of pdfFiles.entries()) {
        setProgressMessage(`Uploading PDF ${index + 1} of ${pdfFiles.length}...`)
        await uploadChecklistPdf(createdChecklist.id, file)
      }

      navigate(`/checklist/edit/${createdChecklist.id}`)
    } catch (error) {
      if (newChecklistId) {
        setErrorMessage(`Checklist was created, but PDF upload failed: ${getErrorMessage(error)}`)
      } else {
        setErrorMessage(`Could not create checklist: ${getErrorMessage(error)}`)
      }
    } finally {
      setIsSubmitting(false)
      setProgressMessage('')
    }
  }

  if (isCheckingAuth) {
    return (
      <main className={styles.page}>
        <p className={styles.message}>Checking session...</p>
      </main>
    )
  }

  if (!isAuthorized) return null

  return (
    <>
      <TopBar onLogout={handleLogout} />
      <main className={styles.page}>
        <button type="button" className={styles.backButton} onClick={() => navigate('/home')}>
          <FiArrowLeft />
          Back to dashboard
        </button>

        <section className={styles.shell}>
          <aside className={styles.introPanel}>
            <p className={styles.eyebrow}>New Checklist</p>
            <h1 className={styles.title}>Start with structure, then add AI context.</h1>
            <p className={styles.subtitle}>
              Create the checklist record first. Any PDFs you attach here are uploaded after creation and linked to the new checklist.
            </p>

            <div className={styles.contextCard}>
              <FiFileText />
              <div>
                <strong>PDF context</strong>
                <span>Specifications, guidelines, manuals, and workflow documents can be attached before creating.</span>
              </div>
            </div>
          </aside>

          <form className={styles.formPanel} onSubmit={handleSubmit} noValidate>
            <div className={styles.fieldGroup}>
              <label htmlFor="checklist-title">Checklist title</label>
              <input
                id="checklist-title"
                type="text"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="Safety inspection checklist"
                disabled={isSubmitting}
                aria-invalid={titleError ? 'true' : 'false'}
              />
              {titleError ? <p className={styles.fieldError}>{titleError}</p> : null}
            </div>

            <div className={styles.fieldGroup}>
              <label htmlFor="checklist-description">Checklist description</label>
              <textarea
                id="checklist-description"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Describe what this checklist should cover."
                rows={6}
                disabled={isSubmitting}
                aria-invalid={descriptionError ? 'true' : 'false'}
              />
              {descriptionError ? <p className={styles.fieldError}>{descriptionError}</p> : null}
            </div>

            <div className={styles.uploadSection}>
              <label className={styles.uploadLabel} htmlFor="pdf-upload">
                <FiUploadCloud />
                <span>Upload PDF context</span>
                <small>Choose one or more PDF files.</small>
              </label>
              <input
                id="pdf-upload"
                className={styles.fileInput}
                type="file"
                accept="application/pdf,.pdf"
                multiple
                onChange={handleFileChange}
                disabled={isSubmitting}
              />

              {pdfFiles.length > 0 ? (
                <div className={styles.fileList}>
                  <div className={styles.fileListHeader}>
                    <span>{pdfFiles.length} PDF{pdfFiles.length === 1 ? '' : 's'} selected</span>
                    <span>{formatFileSize(totalUploadSize)}</span>
                  </div>

                  {pdfFiles.map((file, index) => (
                    <div className={styles.fileRow} key={`${file.name}-${file.lastModified}-${index}`}>
                      <FiFileText />
                      <div>
                        <strong>{file.name}</strong>
                        <span>{formatFileSize(file.size)}</span>
                      </div>
                      <button type="button" onClick={() => removePdf(index)} disabled={isSubmitting} aria-label={`Remove ${file.name}`}>
                        <FiX />
                      </button>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>

            {errorMessage ? (
              <div className={styles.errorBox} role="alert">
                <p>{errorMessage}</p>
                {createdChecklistId ? (
                  <button type="button" onClick={() => navigate(`/checklist/edit/${createdChecklistId}`)}>
                    Open created checklist
                  </button>
                ) : null}
              </div>
            ) : null}

            {isSubmitting ? <p className={styles.message}>{progressMessage}</p> : null}

            <div className={styles.actions}>
              <button type="button" className={styles.secondaryButton} onClick={() => navigate('/home')} disabled={isSubmitting}>
                Cancel
              </button>
              <button type="submit" className={styles.primaryButton} disabled={isSubmitting}>
                {isSubmitting ? 'Creating...' : 'Create checklist'}
              </button>
            </div>
          </form>
        </section>
      </main>
    </>
  )
}

export default NewChecklistPage
