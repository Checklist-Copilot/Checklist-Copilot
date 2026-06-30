import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { FiMenu, FiMail, FiEye, FiEyeOff } from 'react-icons/fi'
import checklyLogo from '../assets/logo.svg'
import styles from '../page-styles/LoginPage.module.css'
import { login } from '../api/auth'
import { ApiError } from '../api/http'
import { getToken } from '../auth/tokenStorage'

function LoginPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [showPassword, setShowPassword] = useState(false)

  function handleLogoClick() {
    navigate(getToken() ? '/home' : '/')
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setErrorMessage(null)
    setIsSubmitting(true)

    try {
      await login({ email, password })
      navigate('/home')
    } catch (error) {
      if (error instanceof ApiError) {
        setErrorMessage(error.message || 'Login failed.')
      } else {
        setErrorMessage('Login failed.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className={styles.page}>
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

      <section className={styles.authSection}>
        <div className={styles.authCard}>
          <h1 className={styles.title}>Welcome back</h1>
          <p className={styles.subtitle}>Welcome back to Checkly</p>

          <form className={styles.form} onSubmit={handleSubmit}>
            <label className={styles.label} htmlFor="login-email">
              Email
            </label>

            <div className={styles.inputWrapper}>
              <input
                className={styles.input}
                id="login-email"
                name="email"
                type="email"
                autoComplete="email"
                placeholder="name@company.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
              <span className={styles.inputIcon}>
                <FiMail />
              </span>
            </div>

            <div className={styles.passwordHeader}>
              <label className={styles.label} htmlFor="login-password">
                Password
              </label>

            </div>

            <div className={styles.inputWrapper}>
              <input
                className={styles.input}
                id="login-password"
                type={showPassword ? 'text' : 'password'}
                name="password"
                autoComplete="current-password"
                placeholder="••••••••"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
              {showPassword ? (
                  <button
                    type="button"
                    className={styles.inputIcon}
                    onClick={() => setShowPassword(false)}
                  >
                    <FiEyeOff />
                  </button>
                ) : (
                  <button
                    type="button"
                    className={styles.inputIcon}
                    onClick={() => setShowPassword(true)}
                  >
                    <FiEye />
                  </button>
                )}
            </div>

            {errorMessage ? <p className={styles.error}>{errorMessage}</p> : null}

            <button className={styles.button} type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Signing in...' : 'Sign in →'}
            </button>
          </form>

          <p className={styles.signupText}>
            No account?{' '}
            <Link to="/register" className={styles.signupLink}>
              Sign up for free
            </Link>
          </p>
        </div>
      </section>
    </main>
  )
}

export default LoginPage
