import styles from '../components-styles/TypingDots.module.css'

type TypingDotsProps = {
  label?: string
  className?: string
}

// Reusable "AI is thinking" indicator. Keeps loading states visibly alive
// without replacing nearby UI text.
export function TypingDots({ label = 'Loading', className = '' }: TypingDotsProps) {
  return (
    <span className={`${styles.wrapper} ${className}`} role="status" aria-label={label}>
      <span className={styles.dot} />
      <span className={styles.dot} />
      <span className={styles.dot} />
    </span>
  )
}
