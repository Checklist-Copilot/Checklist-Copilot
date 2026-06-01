import { Link } from 'react-router-dom'
import {
  FiMenu,
  FiPlay,
  FiCamera,
  FiList,
} from 'react-icons/fi'
import { HiOutlineSparkles } from 'react-icons/hi2'
import styles from '../page-styles/LandingPage.module.css'

function LandingPage() {
  return (
    <main className={styles.page}>
      <div className={styles.ambient} aria-hidden="true">
        <span className={styles.orbOne} />
        <span className={styles.orbTwo} />
        <span className={styles.gridGlow} />
      </div>

      <header className={styles.topbar}>
        <div className={styles.left}>
          <button className={styles.menuButton} type="button">
            <FiMenu />
          </button>

          <img src="/src/assets/logo_cropped.png" alt="Checkly logo" className={styles.logo} />
        </div>

        <div className={styles.topbarActions}>
          <Link to="/login" className={styles.loginButton}>
            Log In
          </Link>

          <Link to="/register" className={styles.getStartedButton}>
            Get Started
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

          <Link to="/login" className={styles.secondaryButton}>
            <FiPlay />
            Watch Demo
          </Link>
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
    </main>
  )
}

export default LandingPage