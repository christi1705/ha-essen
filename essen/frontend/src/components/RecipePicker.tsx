import { Clock, Search } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { api, type Recipe } from '../api'
import { fmtMinutes, shelfText, shelfTone, cls } from '../util'
import Modal from './Modal'

interface Props {
  open: boolean
  title: string
  onClose: () => void
  onPick: (choice: { recipe_id?: string; title?: string }) => void
  /** Tage seit der Abholung am gewählten Tag (für Haltbarkeits-Hinweis) */
  offset?: number
  allowFreeText?: boolean
}

export default function RecipePicker({ open, title, onClose, onPick, offset, allowFreeText = true }: Props) {
  const [recipes, setRecipes] = useState<Recipe[]>([])
  const [q, setQ] = useState('')
  useEffect(() => {
    if (open) {
      setQ('')
      api.recipes().then(setRecipes).catch(() => {})
    }
  }, [open])
  const list = useMemo(() => {
    const ql = q.trim().toLowerCase()
    return recipes.filter((r) => !ql || r.title.toLowerCase().includes(ql) || r.tags.some((t) => t.toLowerCase().includes(ql)))
  }, [recipes, q])

  return (
    <Modal open={open} onClose={onClose} title={title} size="lg">
      <div className="relative mb-3">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <input className="input pl-9" placeholder="Rezept suchen …" value={q} onChange={(e) => setQ(e.target.value)} autoFocus />
      </div>
      {allowFreeText && q.trim() && (
        <button className="btn-outline mb-3 w-full justify-start" onClick={() => onPick({ title: q.trim() })}>
          „{q.trim()}“ ohne Rezept eintragen
        </button>
      )}
      <ul className="divide-y divide-slate-100 dark:divide-slate-800">
        {list.map((r) => {
          const late = offset !== undefined && r.deadline_days < offset
          return (
            <li key={r.id}>
              <button className="flex w-full items-center gap-3 py-2.5 text-left" onClick={() => onPick({ recipe_id: r.id })}>
                <div className="h-11 w-11 shrink-0 overflow-hidden rounded-lg bg-slate-100 dark:bg-slate-800">
                  {r.image_url && <img src={r.image_url} alt="" className="h-full w-full object-cover" referrerPolicy="no-referrer" />}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{r.title}</p>
                  <p className="flex items-center gap-2 text-xs text-slate-500">
                    {(r.total_minutes || r.prep_minutes) && <span className="inline-flex items-center gap-1"><Clock size={12} />{fmtMinutes(r.total_minutes || r.prep_minutes)}</span>}
                    {r.deadline_days < 99 && <span className={cls('chip', late ? 'bg-red-100 text-red-700' : shelfTone(r.deadline_days))}>{late ? 'zu spät in der Woche' : shelfText(r.deadline_days)}</span>}
                  </p>
                </div>
              </button>
            </li>
          )
        })}
        {list.length === 0 && <li className="py-6 text-center text-sm text-slate-500">Keine Rezepte gefunden</li>}
      </ul>
    </Modal>
  )
}
