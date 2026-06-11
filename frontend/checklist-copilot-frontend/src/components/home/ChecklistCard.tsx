import { Link } from 'react-router-dom'
import { FaCalendarAlt, FaFileAlt, FaPlay, FaUser } from 'react-icons/fa'
import { FaRegEdit } from 'react-icons/fa'
import { ImBin } from 'react-icons/im'
import type { ChecklistSummary } from '../../types/checklist'
import styles from '../../page-styles/HomePage.module.css'
import { getChecklistStatus } from './homePageUtils'

type ChecklistCardProps = {
  checklist: ChecklistSummary
  isSelected: boolean
  ownerName: string
  onViewStats: (id: string) => void
}

export function ChecklistCard({ checklist, isSelected, ownerName, onViewStats }: ChecklistCardProps) {
  const status = getChecklistStatus(checklist)
  const badgeClassName =
    status === 'Completed'
      ? styles.completedBadge
      : status === 'Not Started'
        ? styles.notStartedBadge
        : styles.progressBadge

  return (
    <article className={`${styles.card} ${isSelected ? styles.selectedCard : ''}`}>
      <div className={styles.cardHeader}>
        <h3>{checklist.title}</h3>
        <span className={badgeClassName}>{status}</span>
      </div>

      <p className={styles.description}>{checklist.description ?? 'No description.'}</p>

      <div className={styles.meta}>
        <span>
          <FaUser />
          {ownerName}
        </span>

        <span>
          <FaCalendarAlt />
          Updated {new Date(checklist.updated_at).toLocaleDateString()}
        </span>
      </div>

      <p className={styles.items}>
        {checklist.completed_items}/{checklist.total_items} items completed
      </p>

      <div className={styles.fileSummary}>
        <FaFileAlt />
        <span>{formatFileSummary(checklist)}</span>
      </div>

      <div className={styles.actions}>
        <button className={styles.statsButton} type="button" onClick={() => onViewStats(checklist.id)}>
          View Stats
        </button>

        <Link to={`/checklist/use/${checklist.id}`} className={styles.useButton}>
          <FaPlay />
          Use Checklist
        </Link>

        <Link to={`/checklist/edit/${checklist.id}`} className={styles.editButton}>
          <FaRegEdit />
          Edit Checklist
        </Link>

        <button className={styles.iconButton} type="button" aria-label={`Delete ${checklist.title}`}>
          <ImBin />
        </button>
      </div>
    </article>
  )
}

function formatFileSummary(checklist: ChecklistSummary) {
  const fileCount = checklist.file_count ?? 0
  const pdfCount = checklist.pdf_count ?? 0
  const imageCount = checklist.image_count ?? 0

  if (fileCount === 0) return 'No context files'

  const parts = [`${fileCount} ${fileCount === 1 ? 'file' : 'files'}`]
  if (pdfCount > 0) parts.push(`${pdfCount} ${pdfCount === 1 ? 'PDF' : 'PDFs'}`)
  if (imageCount > 0) parts.push(`${imageCount} ${imageCount === 1 ? 'image' : 'images'}`)

  return parts.join(' · ')
}
