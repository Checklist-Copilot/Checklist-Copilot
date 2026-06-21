import { useEffect, useRef, useState } from 'react'
import { FiCamera, FiRefreshCw, FiX } from 'react-icons/fi'
import styles from '../components-styles/CameraCaptureModal.module.css'

type CameraCaptureModalProps = {
  isOpen: boolean
  onCapture: (file: File) => void
  onClose: () => void
}

// Opens the device camera with getUserMedia and converts one captured frame into
// a File so the existing AI image upload flow can handle it like gallery images.
export function CameraCaptureModal({ isOpen, onCapture, onClose }: CameraCaptureModalProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isStarting, setIsStarting] = useState(false)
  const [facingMode, setFacingMode] = useState<'environment' | 'user'>('environment')

  useEffect(() => {
    if (!isOpen) return
    void startCamera()

    return () => stopCamera()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, facingMode])

  async function startCamera() {
    stopCamera()
    setIsStarting(true)
    setError(null)

    try {
      if (!window.isSecureContext) {
        throw new Error('Camera access requires HTTPS or localhost.')
      }
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error('This browser does not support direct camera access.')
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: facingMode } },
        audio: false,
      })
      streamRef.current = stream

      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }
    } catch (err) {
      setError(describeCameraError(err))
    } finally {
      setIsStarting(false)
    }
  }

  function stopCamera() {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    if (videoRef.current) videoRef.current.srcObject = null
  }

  function closeModal() {
    stopCamera()
    onClose()
  }

  async function capturePhoto() {
    const video = videoRef.current
    if (!video || video.videoWidth === 0 || video.videoHeight === 0) return

    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const context = canvas.getContext('2d')
    if (!context) return

    context.drawImage(video, 0, 0, canvas.width, canvas.height)
    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, 'image/jpeg', 0.9),
    )
    if (!blob) return

    onCapture(new File([blob], `camera-${Date.now()}.jpg`, { type: 'image/jpeg' }))
    closeModal()
  }

  if (!isOpen) return null

  return (
    <div className={styles.backdrop} role="dialog" aria-modal="true" aria-label="Take a photo">
      <section className={styles.modal}>
        <header className={styles.header}>
          <strong>Take a photo</strong>
          <button type="button" className={styles.iconButton} onClick={closeModal} aria-label="Close camera">
            <FiX />
          </button>
        </header>

        <div className={styles.previewFrame}>
          <video ref={videoRef} className={styles.video} playsInline muted autoPlay />
          {isStarting ? <p className={styles.status}>Opening camera…</p> : null}
          {error ? <p className={styles.error}>{error}</p> : null}
        </div>

        <div className={styles.actions}>
          <button
            type="button"
            className={styles.secondaryButton}
            onClick={() => setFacingMode((current) => (current === 'environment' ? 'user' : 'environment'))}
            disabled={isStarting}
          >
            <FiRefreshCw />
            Switch camera
          </button>
          <button type="button" className={styles.captureButton} onClick={capturePhoto} disabled={isStarting || !!error}>
            <FiCamera />
            Capture
          </button>
        </div>
      </section>
    </div>
  )
}

function describeCameraError(error: unknown) {
  if (error instanceof DOMException) {
    if (error.name === 'NotAllowedError' || error.name === 'SecurityError') {
      return 'Camera access is blocked. Allow Camera in your browser site settings and try again.'
    }
    if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
      return 'No camera was found on this device.'
    }
    if (error.name === 'NotReadableError' || error.name === 'TrackStartError') {
      return 'The camera is already in use by another app or browser tab.'
    }
    return `Could not open the camera: ${error.message || error.name}`
  }

  if (error instanceof Error) return error.message
  return 'Could not open the camera on this device.'
}
