import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  FiMenu,
  FiPlay,
  FiCamera,
  FiList,
} from 'react-icons/fi'
import { HiOutlineSparkles } from 'react-icons/hi2'
import checklyLogo from '../assets/logo.svg'
import styles from '../page-styles/LandingPage.module.css'
import { getToken } from '../auth/tokenStorage'

function LandingPage() {
  const navigate = useNavigate()
  const [isDemoOpen, setIsDemoOpen] = useState(false)

  function handleLogoClick() {
    navigate(getToken() ? '/home' : '/')
  }

  useEffect(() => {
    if (!isDemoOpen) return

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') setIsDemoOpen(false)
    }

    document.body.style.overflow = 'hidden'
    window.addEventListener('keydown', handleKeyDown)

    return () => {
      document.body.style.overflow = ''
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [isDemoOpen])

  return (
    <main className={styles.page}>
      <div className={styles.ambient} aria-hidden="true">
        <span className={styles.orbOne} />
        <span className={styles.orbTwo} />
      </div>

      <header className={styles.topbar}>
        <div className={styles.left}>
          <button className={styles.menuButton} type="button">
            <FiMenu />
          </button>

          <img
            src={checklyLogo}
            alt="Checkly logo"
            className={styles.logo}
            role="button"
            tabIndex={0}
            onClick={handleLogoClick}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') handleLogoClick()
            }}
          />
        </div>

        <div className={styles.topbarActions}>
          <Link to="/login" className={styles.loginButton}>
            Log In
          </Link>

          <Link to="/register" className={styles.getStartedButton}>
            <span className={styles.getStartedFull}>Get Started</span>
            <span className={styles.getStartedShort}>Start</span>
          </Link>
        </div>
      </header>

      <section className={styles.hero}>
        <div className={styles.heroBadge}>AI checklist copilot</div>
        <h1 className={styles.title}>
          Checklists that actually
          <br />
          think with you
        </h1>

        <p className={styles.subtitle}>
          Build inspection forms, verify them with photos, and keep every review moving from one workspace.
        </p>

        <div className={styles.actions}>
          <Link to="/register" className={styles.primaryButton}>
            → Start for Free
          </Link>

          <button
            type="button"
            className={styles.secondaryButton}
            onClick={() => setIsDemoOpen(true)}
          >
            <FiPlay />
            Watch Demo
          </button>
        </div>

        <div className={styles.featureGrid}>
          <div className={styles.featureCard}>
            <div className={styles.yellowIcon}>
              <FiCamera />
            </div>
            <h2>Photo checks</h2>
            <p>Visual verification</p>
          </div>

          <div className={styles.featureCard}>
            <div className={styles.blueIcon}>
              <HiOutlineSparkles />
            </div>
            <h2>AI Assistant</h2>
            <p>Smart verification</p>
          </div>

          <div className={styles.featureCard}>
            <div className={styles.greenIcon}>
              <FiList />
            </div>
            <h2>Designer</h2>
            <p>Drag-and-drop</p>
          </div>
        </div>
      </section>

      {isDemoOpen && (
        <div
          className={styles.demoOverlay}
          role="dialog"
          aria-modal="true"
          aria-label="Product demo video"
          onClick={() => setIsDemoOpen(false)}
        >
          <div className={styles.demoModal} onClick={(event) => event.stopPropagation()}>
            <button
              type="button"
              className={styles.demoCloseButton}
              aria-label="Close demo video"
              onClick={() => setIsDemoOpen(false)}
            >
              ×
            </button>

            <video className={styles.demoVideo} src="/demo.mp4" controls autoPlay />
          </div>
        </div>
      )}
    </main>
  )
}

export default LandingPage