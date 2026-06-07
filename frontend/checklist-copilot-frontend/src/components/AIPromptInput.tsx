import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent, KeyboardEvent } from 'react'
import { FiPaperclip, FiMic, FiMicOff, FiSend, FiX } from 'react-icons/fi'
import styles from '../components-styles/AIPromptInput.module.css'

// Browser-native speech-to-text. Lives on `window.SpeechRecognition` (spec)
// or `window.webkitSpeechRecognition` (Chrome/Edge). TypeScript doesn't ship
// types for it; minimal subset declared inline.
interface SpeechRecognitionAlternative {
  transcript: string
  confidence: number
}
interface SpeechRecognitionResult {
  readonly length: number
  [index: number]: SpeechRecognitionAlternative
}
interface SpeechRecognitionResultList {
  readonly length: number
  [index: number]: SpeechRecognitionResult
}
interface SpeechRecognitionEvent {
  results: SpeechRecognitionResultList
}
interface SpeechRecognitionErrorEvent {
  error: string
  message?: string
}
interface SpeechRecognition {
  lang: string
  continuous: boolean
  interimResults: boolean
  onresult: ((event: SpeechRecognitionEvent) => void) | null
  onstart: (() => void) | null
  onend: (() => void) | null
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null
  start: () => void
  stop: () => void
}

// Translate raw Web-Speech-API error codes into something the user can act on.
function describeSpeechError(code: string): string {
  switch (code) {
    case 'not-allowed':
    case 'service-not-allowed':
      return 'Microphone access blocked. Click the 🔒 icon in the address bar → Site settings → allow Microphone, then try again.'
    case 'no-speech':
      return "Didn't catch any speech — try again."
    case 'audio-capture':
      return 'No microphone found on this machine.'
    case 'network':
      return 'Network error. Chrome routes speech recognition through Google servers — check your connection.'
    case 'aborted':
      return '' // user-initiated stop, no message needed
    default:
      return `Mic error: ${code}`
  }
}
function getSpeechRecognitionCtor(): (new () => SpeechRecognition) | null {
  if (typeof window === 'undefined') return null
  const w = window as unknown as {
    SpeechRecognition?: new () => SpeechRecognition
    webkitSpeechRecognition?: new () => SpeechRecognition
  }
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null
}

function describeMediaDevicesError(error: unknown): string {
  if (error instanceof DOMException) {
    switch (error.name) {
      case 'NotAllowedError':
      case 'SecurityError':
        return 'Microphone access is blocked for this site. Allow microphone access in your browser settings, then try again.'
      case 'NotFoundError':
      case 'DevicesNotFoundError':
        return 'No microphone found on this machine.'
      case 'NotReadableError':
      case 'TrackStartError':
        return 'Your microphone is already in use by another app or tab.'
      default:
        return `Could not access the microphone: ${error.message || error.name}`
    }
  }
  if (error instanceof Error && error.message) return error.message
  return 'Could not access the microphone. Check your browser microphone permission and try again.'
}

async function requestMicrophoneAccess(): Promise<MediaStream> {
  if (typeof window !== 'undefined' && !window.isSecureContext) {
    throw new Error('Microphone access requires HTTPS or localhost.')
  }
  if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
    throw new Error('Microphone permission requests are not supported in this browser.')
  }

  // This explicitly asks the browser for microphone access, matching the common
  // permission-check pattern: getUserMedia resolves only when access is granted.
  // Keep the stream alive until SpeechRecognition starts; stopping it too early
  // can make some browsers immediately report the mic as blocked again.
  return navigator.mediaDevices.getUserMedia({ audio: true })
}

function stopMicrophoneStream(stream: MediaStream | null) {
  stream?.getTracks().forEach((track) => track.stop())
}

export type AIPromptInputProps = {
  value: string
  onChange: (next: string) => void
  onSubmit: () => void
  // Files attached via the paperclip button. Parent decides what to do with them
  // (PDFs as references on create, images as vision inputs on edit, etc.).
  attachedFiles?: File[]
  onAttachFiles?: (files: File[]) => void
  onRemoveFile?: (index: number) => void
  // Restrict the file picker's accept attribute. Defaults to everything.
  accept?: string
  disabled?: boolean
  placeholder?: string
  // Visual label for the "submit/send" tooltip — e.g. "Generate" on the new
  // page, "Send" inside the AI panel of the edit page.
  submitLabel?: string
}

function AIPromptInput({
  value,
  onChange,
  onSubmit,
  attachedFiles = [],
  onAttachFiles,
  onRemoveFile,
  accept,
  disabled = false,
  placeholder = 'Describe what you want to do…',
  submitLabel = 'Send',
}: AIPromptInputProps) {
  // Speech setup.
  const SpeechRecognitionCtor = getSpeechRecognitionCtor()
  const speechSupported = SpeechRecognitionCtor !== null
  const recognitionRef = useRef<SpeechRecognition | null>(null)
  const [isListening, setIsListening] = useState(false)
  // Visible feedback when the mic fails — without this, denied permission or
  // a network error to Google's speech servers looked like "button does nothing."
  const [micError, setMicError] = useState<string | null>(null)

  // Auto-grow textarea: keep its height in sync with content so the user can
  // see everything they've typed up to a CSS-defined max (then it scrolls).
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    // Reset before measuring so we can shrink as well as grow.
    el.style.height = 'auto'
    el.style.height = `${el.scrollHeight}px`
  }, [value])

  useEffect(() => {
    return () => {
      try {
        recognitionRef.current?.stop()
      } catch {
        /* recognition wasn't running */
      }
    }
  }, [])

  async function toggleMic() {
    if (!SpeechRecognitionCtor) {
      setMicError('Voice input is only supported in Chrome or Edge. Firefox can access your microphone, but does not support browser speech recognition.')
      return
    }
    if (isListening) {
      try {
        recognitionRef.current?.stop()
      } catch {
        /* noop */
      }
      setIsListening(false)
      return
    }

    let permissionStream: MediaStream | null = null
    try {
      setMicError(null)
      permissionStream = await requestMicrophoneAccess()
    } catch (err) {
      // Calling getUserMedia explicitly triggers the browser permission prompt
      // when possible. If the user previously blocked the site, browsers will
      // reject immediately and the user must unblock it from site settings.
      // eslint-disable-next-line no-console
      console.warn('[speech] microphone permission failed:', err)
      setIsListening(false)
      setMicError(describeMediaDevicesError(err))
      return
    }

    const rec = new SpeechRecognitionCtor()
    rec.lang = 'en-US'
    rec.continuous = false
    rec.interimResults = false
    rec.onresult = (event) => {
      const transcript = event.results[0][0].transcript
      onChange(value ? `${value.trim()} ${transcript}` : transcript)
    }
    rec.onstart = () => {
      // eslint-disable-next-line no-console
      console.log('[speech] listening…')
      stopMicrophoneStream(permissionStream)
      permissionStream = null
      setMicError(null)
    }
    rec.onend = () => {
      // eslint-disable-next-line no-console
      console.log('[speech] ended')
      stopMicrophoneStream(permissionStream)
      permissionStream = null
      setIsListening(false)
    }
    rec.onerror = (event) => {
      // eslint-disable-next-line no-console
      console.warn('[speech] error:', event.error, event)
      stopMicrophoneStream(permissionStream)
      permissionStream = null
      setIsListening(false)
      const message = describeSpeechError(event.error)
      if (message) setMicError(message)
    }
    try {
      rec.start()
      recognitionRef.current = rec
      setIsListening(true)
      setMicError(null)
    } catch (err) {
      // .start() throws if recognition is already active or if the browser
      // refuses to begin (e.g. permission previously denied without ever
      // prompting again). Surface it instead of failing silently.
      // eslint-disable-next-line no-console
      console.warn('[speech] start() failed:', err)
      stopMicrophoneStream(permissionStream)
      setIsListening(false)
      setMicError(
        'Could not start the microphone. Check the browser site permissions and allow Microphone.',
      )
    }
  }

  function handleFilesSelected(event: ChangeEvent<HTMLInputElement>) {
    const incoming = Array.from(event.target.files ?? [])
    if (incoming.length > 0) onAttachFiles?.(incoming)
    event.target.value = ''
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    // Enter sends; Shift+Enter inserts a newline (familiar OpenAI behaviour).
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      if (!disabled && value.trim()) onSubmit()
    }
  }

  const canSubmit = !disabled && value.trim().length > 0

  return (
    <div className={styles.wrapper} data-disabled={disabled || undefined}>
      <textarea
        ref={textareaRef}
        className={styles.textarea}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        rows={1}
        disabled={disabled}
      />

      {attachedFiles.length > 0 ? (
        <ul className={styles.fileChips}>
          {attachedFiles.map((file, index) => (
            <li key={`${file.name}-${index}`} className={styles.fileChip}>
              <FiPaperclip className={styles.chipIcon} />
              <span className={styles.chipName}>{file.name}</span>
              {onRemoveFile ? (
                <button
                  type="button"
                  className={styles.chipRemove}
                  onClick={() => onRemoveFile(index)}
                  aria-label={`Remove ${file.name}`}
                >
                  <FiX />
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}

      <div className={styles.toolbar}>
        <div className={styles.leftTools}>
          {onAttachFiles ? (
            <label
              className={styles.iconButton}
              title="Attach files"
              aria-label="Attach files"
            >
              <FiPaperclip />
              <input
                type="file"
                multiple
                accept={accept}
                onChange={handleFilesSelected}
                className={styles.hiddenFileInput}
                disabled={disabled}
              />
            </label>
          ) : null}
          <button
            type="button"
            className={`${styles.iconButton} ${isListening ? styles.micActive : ''}`}
            onClick={toggleMic}
            disabled={disabled || !speechSupported}
            title={
              speechSupported
                ? isListening
                  ? 'Stop dictation'
                  : 'Dictate via your browser microphone'
                : 'Voice input is only supported in Chrome or Edge'
            }
            aria-label={isListening ? 'Stop dictation' : 'Start dictation'}
          >
            {isListening ? <FiMicOff /> : <FiMic />}
          </button>
        </div>
        <button
          type="button"
          className={styles.sendButton}
          onClick={() => canSubmit && onSubmit()}
          disabled={!canSubmit}
          title={submitLabel}
          aria-label={submitLabel}
        >
          <FiSend />
        </button>
      </div>

      {micError ? (
        <p className={styles.micError} role="alert">
          {micError}
        </p>
      ) : null}
    </div>
  )
}

export default AIPromptInput
