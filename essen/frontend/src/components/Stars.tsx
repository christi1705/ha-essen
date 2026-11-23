import { Star } from 'lucide-react'
import { cls } from '../util'

export default function Stars({ value, onRate, size = 16 }: { value: number | null; onRate?: (n: number) => void; size?: number }) {
  return (
    <span className="inline-flex items-center">
      {[1, 2, 3, 4, 5].map((n) => {
        const filled = value !== null && value >= n - 0.25
        const icon = <Star size={size} className={cls(filled ? 'fill-amber-400 text-amber-400' : 'text-slate-300 dark:text-slate-600')} />
        return onRate ? (
          <button key={n} type="button" className="p-0.5" onClick={() => onRate(n)} aria-label={`${n} Sterne`}>{icon}</button>
        ) : (
          <span key={n}>{icon}</span>
        )
      })}
    </span>
  )
}
