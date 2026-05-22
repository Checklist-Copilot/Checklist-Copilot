import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import styles from '../page-styles/RegisterPage.module.css'
import { registerUser } from '../api/user'
import { ApiError } from '../api/http'
import { saveToken } from '../auth/tokenStorage'

function RegisterPage() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
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
      <section className={styles.card}>
        <h1 className={styles.title}>Register</h1>
        <form className={styles.form} onSubmit={handleSubmit}>
          <label className={styles.label} htmlFor='register-username'>Username</label>
          <input
            className={styles.input}
            id='register-username'
            name='username'
            type='text'
            autoComplete='username'
            placeholder='Choose a username'
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            required
          />

          <label className={styles.label} htmlFor='register-email'>Email</label>
          <input
            className={styles.input}
            id='register-email'
            name='email'
            type='email'
            autoComplete='email'
            placeholder='you@example.com'
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />

          <label className={styles.label} htmlFor='register-password'>Password</label>
          <input
            className={styles.input}
            id='register-password'
            name='password'
            type='password'
            autoComplete='new-password'
            placeholder='Create a password'
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />

          {errorMessage ? <p className={styles.error}>{errorMessage}</p> : null}

          <button className={styles.button} type='submit' disabled={isSubmitting}>
            {isSubmitting ? 'Registering...' : 'Register'}
          </button>
        </form>
      </section>
    </main>
  )
}

export default RegisterPage
