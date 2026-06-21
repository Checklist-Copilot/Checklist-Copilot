import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import checklyLogo from '../assets/logo_cropped.png'
import styles from '../page-styles/RegisterPage.module.css'
import { registerUser } from '../api/user'
import { ApiError } from '../api/http'
import { saveToken } from '../auth/tokenStorage'
import { FiMenu, FiMail, FiEye, FiUser, FiEyeOff } from 'react-icons/fi'

function RegisterPage() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (password !== confirmPassword) {
      setErrorMessage('Passwords do not match.')
      setIsSubmitting(false)
      return
    }
    setErrorMessage(null)
    setIsSubmitting(true)

    try {
      const response = await registerUser({ username, email, password })
      saveToken(response.access_token)
      navigate('/home')
    } catch (error) {
      if (error instanceof ApiError) {
        setErrorMessage(error.message || 'Registration failed.')
      } else {
        setErrorMessage('Registration failed.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className={styles.page}>
      <header className={styles.topbar}>
        <div className={styles.left}>
          <button className={styles.menuButton} type='button'>
            <FiMenu />
          </button>

          <img src={checklyLogo} alt='Checkly logo' className={styles.logo} />
        </div>

        <div className={styles.topbarActions}>
          <Link to='/login' className={styles.loginButton}>
            Log In
          </Link>

          <Link to='/register' className={styles.getStartedButton}>
            <span className={styles.getStartedFull}>Get Started</span>
            <span className={styles.getStartedShort}>Start</span>
          </Link>
        </div>
      </header>

      <section className={styles.authSection}>
        <div className={styles.authCard}>
          <h1 className={styles.title}>Get started</h1>

          <p className={styles.subtitle}>
            Create your Checkly account
          </p>

          <form className={styles.form} onSubmit={handleSubmit}>
            <label className={styles.label} htmlFor='register-username'>
              Your name
            </label>

            <div className={styles.inputWrapper}>
              <input
                className={styles.input}
                id='register-username'
                name='username'
                type='text'
                autoComplete='username'
                placeholder='John Doe'
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                required
              />
              <span className={styles.inputIcon}>
                <FiUser />
              </span>
            </div>

            <label className={styles.label} htmlFor='register-email'>
              Email
            </label>

            <div className={styles.inputWrapper}>
              <input
                className={styles.input}
                id='register-email'
                name='email'
                type='email'
                autoComplete='email'
                placeholder='name@company.com'
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
              <span className={styles.inputIcon}>
                <FiMail />
              </span>
            </div>

            <label className={styles.label} htmlFor='register-password'>
              Password
            </label>

            <div className={styles.inputWrapper}>
              <input
                className={styles.input}
                id='register-password'
                name='password'
                type={showPassword ? 'text' : 'password'}
                autoComplete='new-password'
                placeholder='••••••••'
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />

              {showPassword ? (
                <button
                  type='button'
                  className={styles.inputIcon}
                  onClick={() => setShowPassword(false)}
                >
                  <FiEyeOff />
                </button>
              ) : (
                <button
                  type='button'
                  className={styles.inputIcon}
                  onClick={() => setShowPassword(true)}
                >
                  <FiEye />
                </button>
              )}
            </div>

            <label className={styles.label} htmlFor='confirm-password'>
              Confirm password
            </label>

            <div className={styles.inputWrapper}>
              <input
                className={styles.input}
                id='confirm-password'
                name='confirm-password'
                type={showConfirmPassword ? 'text' : 'password'}
                autoComplete='new-password'
                placeholder='••••••••'
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                required
              />

              {showConfirmPassword ? (
                <button
                  type='button'
                  className={styles.inputIcon}
                  onClick={() => setShowConfirmPassword(false)}
                >
                  <FiEyeOff />
                </button>
              ) : (
                <button
                  type='button'
                  className={styles.inputIcon}
                  onClick={() => setShowConfirmPassword(true)}
                >
                  <FiEye />
                </button>
              )}
            </div>

            {errorMessage ? (
              <p className={styles.error}>{errorMessage}</p>
            ) : null}

            <button
              className={styles.button}
              type='submit'
              disabled={isSubmitting}
            >
              {isSubmitting
                ? 'Creating account...'
                : 'Create account →'}
            </button>
          </form>

          <p className={styles.signupText}>
            Already have an account?{' '}
            <Link to='/login' className={styles.signupLink}>
              Log in
            </Link>
          </p>
        </div>
      </section>
    </main>
  )
}

export default RegisterPage
