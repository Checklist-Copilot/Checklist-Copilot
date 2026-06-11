import type { ChecklistSummary } from '../../types/checklist'
import styles from '../../page-styles/HomePage.module.css'
import type { ActivityMode } from './types'
import { getActivityDays } from './homePageUtils'

type RecentActivityPanelProps = {
  checklists: ChecklistSummary[]
  selectedChecklist: ChecklistSummary | null
  activityMode: ActivityMode
  onActivityModeChange: (mode: ActivityMode) => void
}

const activityLabelByMode = {
  created: 'created',
  inProgress: 'set in progress',
  completed: 'completed',
} satisfies Record<ActivityMode, string>

export function RecentActivityPanel({
  checklists,
  selectedChecklist,
  activityMode,
  onActivityModeChange,
}: RecentActivityPanelProps) {
  const activityDays = getActivityDays(selectedChecklist ? [selectedChecklist] : checklists, activityMode)
  const maxActivityCount = Math.max(...activityDays.map((day) => day.count), 1)
  const activityAxisLabels = Array.from(new Set([maxActivityCount, Math.floor(maxActivityCount / 2), 0]))

  return (
    <div className={`${styles.panel} ${styles.activityPanel}`}>
      <div className={styles.panelHeader}>
        <div>
          <h2 className={styles.panelTitle}>Recent Activity</h2>
          <p className={styles.panelSubtitle}>
            {activityLabelByMode[activityMode]} checklists over the last 7 days
          </p>
        </div>

        <div className={styles.segmentedControl} aria-label="Activity type">
          <button
            type="button"
            className={activityMode === 'created' ? styles.segmentActive : ''}
            onClick={() => onActivityModeChange('created')}
          >
            Created
          </button>
          <button
            type="button"
            className={activityMode === 'inProgress' ? styles.segmentActive : ''}
            onClick={() => onActivityModeChange('inProgress')}
          >
            In Progress
          </button>
          <button
            type="button"
            className={activityMode === 'completed' ? styles.segmentActive : ''}
            onClick={() => onActivityModeChange('completed')}
          >
            Completed
          </button>
        </div>
      </div>

      <div className={styles.chartShell}>
        <div className={styles.chartAxis} aria-hidden="true">
          {activityAxisLabels.map((label) => (
            <span key={label}>{label}</span>
          ))}
        </div>

        <div className={styles.chart}>
          {activityDays.map((day, index) => {
            const height = day.count === 0 ? 7 : Math.max(16, Math.round((day.count / maxActivityCount) * 100))

            return (
              <div
                className={styles.barGroup}
                key={day.key}
                title={`${day.count} checklist${day.count === 1 ? '' : 's'} ${activityLabelByMode[activityMode]}`}
              >
                <div
                  className={`${styles.bar} ${index === activityDays.length - 1 ? styles.activeBar : ''}`}
                  style={{ height: `${height}px` }}
                  aria-label={`${day.count} checklist${day.count === 1 ? '' : 's'} ${activityLabelByMode[activityMode]} on ${day.label}`}
                />
                <span>{day.label}</span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
