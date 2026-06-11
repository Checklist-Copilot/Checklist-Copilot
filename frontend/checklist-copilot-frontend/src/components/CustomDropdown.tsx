import { useEffect, useId, useRef, useState } from 'react'
import type { KeyboardEvent } from 'react'
import styles from '../components-styles/CustomDropdown.module.css'

export type DropdownOption<T extends string> = {
  value: T
  label: string
  tone?: 'neutral' | 'red' | 'yellow' | 'green' | 'purple'
}

type CustomDropdownProps<T extends string> = {
  label: string
  value: T
  options: DropdownOption<T>[]
  onChange: (value: T) => void
  disabled?: boolean
  className?: string
}

function CustomDropdown<T extends string>({
  label,
  value,
  options,
  onChange,
  disabled = false,
  className = '',
}: CustomDropdownProps<T>) {
  const dropdownId = useId()
  const rootRef = useRef<HTMLDivElement>(null)
  const [isOpen, setIsOpen] = useState(false)
  const selectedIndex = Math.max(options.findIndex((option) => option.value === value), 0)
  const [activeIndex, setActiveIndex] = useState(selectedIndex)
  const selectedOption = options[selectedIndex]

  useEffect(() => {
    if (!isOpen) return

    function handlePointerDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handlePointerDown)
    return () => document.removeEventListener('mousedown', handlePointerDown)
  }, [isOpen])

  function selectOption(option: DropdownOption<T>) {
    onChange(option.value)
    setIsOpen(false)
  }

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (disabled) return

    if (event.key === 'Escape') {
      setIsOpen(false)
      return
    }

    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()
      setIsOpen(true)
      setActiveIndex((current) => {
        const direction = event.key === 'ArrowDown' ? 1 : -1
        return (current + direction + options.length) % options.length
      })
      return
    }

    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      if (!isOpen) {
        setIsOpen(true)
        setActiveIndex(selectedIndex)
        return
      }
      selectOption(options[activeIndex])
    }
  }

  return (
    <div
      ref={rootRef}
      className={`${styles.dropdown} ${className}`}
      onKeyDown={handleKeyDown}
      data-open={isOpen ? 'true' : 'false'}
    >
      <span id={`${dropdownId}-label`} className={styles.visuallyHidden}>
        {label}
      </span>
      <button
        type="button"
        className={styles.trigger}
        aria-labelledby={`${dropdownId}-label ${dropdownId}-value`}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-controls={`${dropdownId}-listbox`}
        disabled={disabled}
        onClick={() => {
          setIsOpen((current) => !current)
          setActiveIndex(selectedIndex)
        }}
      >
        <span className={`${styles.statusDot} ${styles[selectedOption?.tone ?? 'neutral']}`} aria-hidden="true" />
        <span id={`${dropdownId}-value`} className={styles.valueText}>
          {selectedOption?.label ?? label}
        </span>
        <span className={styles.chevron} aria-hidden="true" />
      </button>

      {isOpen ? (
        <div
          id={`${dropdownId}-listbox`}
          className={styles.menu}
          role="listbox"
          aria-labelledby={`${dropdownId}-label`}
          aria-activedescendant={`${dropdownId}-option-${activeIndex}`}
        >
          {options.map((option, index) => (
            <button
              id={`${dropdownId}-option-${index}`}
              key={option.value}
              type="button"
              role="option"
              aria-selected={option.value === value}
              className={styles.option}
              data-active={index === activeIndex ? 'true' : 'false'}
              onMouseEnter={() => setActiveIndex(index)}
              onClick={() => selectOption(option)}
            >
              <span className={`${styles.statusDot} ${styles[option.tone ?? 'neutral']}`} aria-hidden="true" />
              <span>{option.label}</span>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  )
}

export default CustomDropdown
