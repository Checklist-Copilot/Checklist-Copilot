import { useEffect, useState } from 'react'
import type { Dispatch, SetStateAction } from 'react'
import checklyRobot from '../assets/checkly.png'
import AIPromptInput from './AIPromptInput'
import { CameraCaptureModal } from './CameraCaptureModal'
import { MarkdownMessage } from './MarkdownMessage'
import styles from '../components-styles/AIChatPopUp.module.css'

type AIChatPopupProps = {
  isOpen: boolean
  messages: ChatMessage[]
  setMessages: Dispatch<SetStateAction<ChatMessage[]>>
  onClose: () => void
  onSendMessage: (message: string, conversation: ChatMessage[], images?: File[]) => Promise<string>
}

export type ChatMessage = {
  id: number
  sender: 'user' | 'checkly'
  text: string
}

function AIChatPopup({ isOpen, messages, setMessages, onClose, onSendMessage }: AIChatPopupProps) {
  const [message, setMessage] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [attachedImages, setAttachedImages] = useState<File[]>([])
  const [isCameraOpen, setIsCameraOpen] = useState(false)
  const [isClosing, setIsClosing] = useState(false)
  const [shouldRender, setShouldRender] = useState(isOpen)

  useEffect(() => {
    const animationFrame = window.requestAnimationFrame(() => {
      if (isOpen) {
        setShouldRender(true)
        setIsClosing(false)
        return
      }

      if (shouldRender) {
        setIsClosing(true)
      }
    })

    return () => window.cancelAnimationFrame(animationFrame)
  }, [isOpen, shouldRender])

  if (!shouldRender) {
    return null
  }

  function handleClose() {
    setIsClosing(true)
  }

  function handleAnimationEnd() {
    if (!isClosing) return
    setShouldRender(false)
    setIsClosing(false)
    onClose()
  }

  // Sends the user's chat message by appending it to the conversation and
  // forwarding it to the page-level AI edit handler. Triggered by AIPromptInput
  // (which fires onSubmit when the user hits Enter or clicks the send button —
  // including after dictating via the mic).
  async function handleSend() {
    const trimmedMessage = message.trim()
    if ((!trimmedMessage && attachedImages.length === 0) || isSending) return

    const imagesForSend = attachedImages
    const uploadNotice = imagesForSend.length > 0 ? `**Uploaded ${imagesForSend.length} ${imagesForSend.length === 1 ? 'image' : 'images'}.**` : ''
    const displayText = [uploadNotice, trimmedMessage].filter(Boolean).join('\n\n')
    const instruction = trimmedMessage || 'Please observe the uploaded image.'
    const conversationWithUserMessage = [
      ...messages,
      { id: Date.now(), sender: 'user' as const, text: displayText },
    ]

    setMessage('')
    setAttachedImages([])
    setMessages(conversationWithUserMessage)
    setIsSending(true)

    try {
      const reply = await onSendMessage(instruction, conversationWithUserMessage, imagesForSend)
      setMessages((currentMessages) => [
        ...currentMessages,
        { id: Date.now() + 1, sender: 'checkly', text: reply || 'Done.' },
      ])
    } catch {
      setMessages((currentMessages) => [
        ...currentMessages,
        {
          id: Date.now() + 1,
          sender: 'checkly',
          text: 'I could not update this checklist. Please try again.',
        },
      ])
    } finally {
      setIsSending(false)
    }
  }

  return (
    <aside
      className={`${styles.popup} ${isClosing ? styles.popupClosing : ''}`}
      aria-label="AI chat popup"
      onAnimationEnd={handleAnimationEnd}
    >
      <header className={styles.header}>
        <div className={styles.titleGroup}>
          <img src={checklyRobot} alt="Checkly robot" className={styles.checklyAvatar} />
          <div>
            <strong className={styles.title}>Checkly</strong>
          </div>
        </div>

        <button
          type="button"
          onClick={handleClose}
          aria-label="Close AI chat"
          className={styles.closeButton}
        >
          ×
        </button>
      </header>

      <div className={styles.messages}>
        {messages.map((chatMessage) => (
          <div
            key={chatMessage.id}
            className={`${styles.messageBubble} ${
              chatMessage.sender === 'user' ? styles.userMessageBubble : ''
            }`}
          >
            <span className={styles.messageLabel}>
              {chatMessage.sender === 'user' ? 'You' : 'Checkly'}
            </span>
            <MarkdownMessage text={chatMessage.text} />
          </div>
        ))}
      </div>

      {/* Same OpenAI-style input as the edit page, plus camera capture so a
          worker can attach photos to the AI prompt before sending. */}
      <div className={styles.inputWrapper}>
        <AIPromptInput
          value={message}
          onChange={setMessage}
          onSubmit={handleSend}
          attachedFiles={attachedImages}
          onAttachFiles={(files) => setAttachedImages((current) => [...current, ...files.filter((file) => file.type.startsWith('image/'))])}
          onRemoveFile={(index) => setAttachedImages((current) => current.filter((_, itemIndex) => itemIndex !== index))}
          accept="image/*"
          enableCamera
          onOpenCamera={() => {
            if (window.isSecureContext && typeof navigator.mediaDevices?.getUserMedia === 'function') {
              setIsCameraOpen(true)
              return true
            }

            return false
          }}
          disabled={isSending}
          placeholder={
            isSending ? 'Updating checklist…' : 'Ask Checkly… or tap the mic.'
          }
          submitLabel="Send"
        />
      </div>

      <CameraCaptureModal
        isOpen={isCameraOpen}
        onCapture={(file) => setAttachedImages((current) => [...current, file])}
        onClose={() => setIsCameraOpen(false)}
      />
    </aside>
  )
}

export default AIChatPopup
