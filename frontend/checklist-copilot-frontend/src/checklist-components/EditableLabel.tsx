import { useEffect, useState } from 'react'
import styles from './EditableLabel.module.css'

type EditableLabelProps = {
  value: string
  fallbackValue: string
  isEditMode?: boolean
  onChange?: (value: string) => void
  ariaLabel?: string
}

export function EditableLabel({
  value,
  fallbackValue,
  isEditMode = false,
  onChange,
  ariaLabel,
}: EditableLabelProps) {
  const [draftValue, setDraftValue] = useState(value)
  const [isFocused, setIsFocused] = useState(false)

  useEffect(() => {
    if (!isFocused) setDraftValue(value)
  }, [isFocused, value])

  if (!isEditMode) return <>{value}</>

  function handleChange(nextValue: string) {
    setDraftValue(nextValue)

    if (nextValue.trim()) {
      onChange?.(nextValue)
    }
  }

  function handleBlur() {
    setIsFocused(false)

    if (!draftValue.trim()) {
      setDraftValue(fallbackValue)
      onChange?.(fallbackValue)
    }
  }

  return (
    <input
      className={styles.input}
      value={isFocused ? draftValue : value}
      aria-label={ariaLabel ?? 'Component label'}
      onFocus={() => {
        setIsFocused(true)
        setDraftValue(value)
      }}
      onBlur={handleBlur}
      onClick={(event) => event.stopPropagation()}
      onChange={(event) => handleChange(event.target.value)}
    />
  )
}
