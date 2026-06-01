import { useState, type FormEvent } from 'react'
import checklyRobot from '../assets/checkly.png'
import styles from '../components-styles/AIChatPopUp.module.css'

type AIChatPopupProps = {
  isOpen: boolean
  onClose: () => void
  onSendMessage: (message: string) => Promise<string>
}

type ChatMessage = {
  id: number
  sender: 'user' | 'checkly'
  text: string
}

function AIChatPopup({ isOpen, onClose, onSendMessage }: AIChatPopupProps) {
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 1,
      sender: 'checkly',
      text: 'Hi, I am Checkly. How can I help you with this checklist?',
    },
  ])
  const [isSending, setIsSending] = useState(false)

  if (!isOpen) {
    return null
  }

  // Handles sending the user's chat message by adding it to the conversation and forwarding it to the page-level AI edit handler.
  // While the request is running, it prevents duplicate sends and then adds Checkly's reply or an error message when the request finishes.
  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const trimmedMessage = message.trim()
    if (!trimmedMessage || isSending) {
      return
    }

    setMessage('')
    setMessages((currentMessages) => [
      ...currentMessages,
      { id: Date.now(), sender: 'user', text: trimmedMessage },
    ])
    setIsSending(true)

    try {
      const reply = await onSendMessage(trimmedMessage)
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
    <aside className={styles.popup} aria-label="AI chat popup">
      <header className={styles.header}>
        <div className={styles.titleGroup}>
          <img src={checklyRobot} alt="Checkly robot" className={styles.checklyAvatar} />
          <div>
            <strong className={styles.title}>Checkly</strong>
          </div>
        </div>

        <button
          type="button"
          onClick={onClose}
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
            <p>{chatMessage.text}</p>
          </div>
        ))}
      </div>

      <form className={styles.form} onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder={isSending ? 'Updating checklist...' : 'Ask something...'}
          className={styles.input}
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          disabled={isSending}
        />
        <button type="submit" className={styles.sendButton} disabled={isSending}>
          {isSending ? 'Sending' : 'Send'}
        </button>
      </form>
    </aside>
  )
}

export default AIChatPopup
