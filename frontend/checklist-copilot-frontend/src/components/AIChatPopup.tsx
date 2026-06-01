import checklyRobot from '../assets/checkly.png'
import styles from '../components-styles/AIChatPopUp.module.css'

type AIChatPopupProps = {
  isOpen: boolean
  onClose: () => void
}

function AIChatPopup({ isOpen, onClose }: AIChatPopupProps) {
  if (!isOpen) {
    return null
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
        <div className={styles.messageBubble}>
          <span className={styles.messageLabel}>Checkly</span>
          <p>Hi, I am Checkly. How can I help you with this checklist?</p>
        </div>
      </div>

      <form className={styles.form} onSubmit={(event) => event.preventDefault()}>
        <input
          type="text"
          placeholder="Ask something..."
          className={styles.input}
        />
        <button type="submit" className={styles.sendButton}>
          Send
        </button>
      </form>
    </aside>
  )
}

export default AIChatPopup
