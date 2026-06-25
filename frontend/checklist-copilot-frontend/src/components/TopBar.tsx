import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FiMenu, FiX, FiGrid, FiPlus, FiLogOut } from 'react-icons/fi'
import { FaUserCircle } from "react-icons/fa";
import checklyLogo from '../assets/logo.svg'
import styles from '../components-styles/TopBar.module.css'

type TopBarProps = {
  userName?: string
  userEmail?: string
  onLogout: () => void
}

function TopBar({ userName = 'User', userEmail = '', onLogout }: TopBarProps) {
  const navigate = useNavigate()
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  function handleNavigate(path: string) {
    setIsMenuOpen(false)
    navigate(path)
  }

  return (
    <header className={styles.topbar}>
      <div className={styles.left}>
        <button
          className={styles.menuButton}
          type="button"
          onClick={() => setIsMenuOpen((prev) => !prev)}
        >
          {isMenuOpen ? <FiX /> : <FiMenu />}
        </button>

        <img src={checklyLogo} alt="Checkly logo" className={styles.logo} />
      </div>

      <button className={styles.logoutButton} type="button" onClick={onLogout} aria-label="Log out">
        <FiLogOut />
        <span>Log Out</span>
      </button>

      {isMenuOpen ? (
        <aside className={styles.sidebar}>
          <div className={styles.userRow}>
            <div className={styles.avatar}>
              {userName.slice(0, 2).toUpperCase()}
            </div>

            <div>
              <p className={styles.userName}>{userName}</p>
              {userEmail ? <p className={styles.userEmail}>{userEmail}</p> : null}
            </div>
          </div>

          <nav className={styles.nav}>
            <button className={styles.navItem} type="button" onClick={() => handleNavigate('/home')}>
              <FiGrid />
              Dashboard
            </button>

            <button className={styles.navItem} type="button" onClick={() => handleNavigate('/checklist/new')}>
              <FiPlus />
              New Checklist
            </button>

            <button className={styles.navItem} type="button" onClick={() => handleNavigate('/account')}>
              <FaUserCircle />
              My Account
            </button>

            <button className={styles.navItem} type="button" onClick={onLogout}>
              <FiLogOut />
              Log Out
            </button>
          </nav>
        </aside>
      ) : null}
    </header>
  )
}

export default TopBar