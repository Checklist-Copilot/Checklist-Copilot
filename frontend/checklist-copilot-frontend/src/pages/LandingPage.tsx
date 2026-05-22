import { Link } from "react-router-dom";
import styles from "../page-styles/LandingPage.module.css";


function LandingPage() {
    return (
        <main className={styles.page}>
            <section className={styles.hero}>
                <h1 className={styles.title}>Checklist Copilot</h1>
                <p className={styles.subtitle}>
                    Build and use checklists with a focused workflow.
                </p>
                <div className={styles.actions}>
                    <Link to="/login" className={styles.primaryButton}>
                        Login
                    </Link>
                    <Link to="/register" className={styles.secondaryButton}>
                        Register
                    </Link>
                </div>
            </section>
        </main>
    )

}

export default LandingPage
