import { useState } from 'react'
import { FiMenu, FiX, FiGrid, FiPlus, FiLogOut } from 'react-icons/fi'
import { FaUserCircle } from "react-icons/fa";
import styles from '../page-styles/TopBar.module.css'

type TopBarProps = {
  userName?: string
  userEmail?: string
  onLogout: () => void
}

function TopBar({ userName = 'User', userEmail = '', onLogout }: TopBarProps) {
  const [isMenuOpen, setIsMenuOpen] = useState(false)

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

        <img src="/src/assets/logo_cropped.png" alt="Checkly logo" className={styles.logo} />
      </div>

      <button className={styles.logoutButton} type="button" onClick={onLogout}>
        Log Out
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
            <a href="/home" className={styles.navItem}>
              <FiGrid />
              Dashboard
            </a>

            <a href="/checklist/new" className={styles.navItem}>
              <FiPlus />
              New Checklist
            </a>

            <a href="/account" className={styles.navItem}>
              <FaUserCircle />
              My Account
            </a>

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