import { Check, Plus, ShoppingCart, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { api, type ShoppingItem } from '../api'
import { cls } from '../util'

function Row({ i, onToggle, onDelete }: { i: ShoppingItem; onToggle: () => void; onDelete: () => void }) {
  return (
    <li className="flex items-center gap-3 py-2">
      <button onClick={onToggle} aria-label={i.checked ? 'Wieder offen' : 'Abhaken'}
        className={cls('flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 transition',
          i.checked ? 'border-brand-600 bg-brand-600 text-white' : 'border-slate-300 hover:border-brand-500 dark:border-slate-600')}>
        {i.checked && <Check size={16} strokeWidth={3} />}
      </button>
      <button onClick={onToggle} className="min-w-0 flex-1 text-left">
        <p className={cls('truncate', i.checked && 'text-slate-400 line-through')}>
          {i.quantity && <span className="font-semibold tabular-nums">{i.quantity} </span>}{i.name}
        </p>
        {(i.sources.length > 0 || i.note) && (
          <p className="truncate text-xs text-slate-500">{[i.note, i.sources.join(', ')].filter(Boolean).join(' · ')}</p>
        )}
      </button>
      <button className="icon-btn h-8 w-8" onClick={onDelete} aria-label="Entfernen"><Trash2 size={16} /></button>
    </li>
  )
}

export default function ShoppingPage() {
  const [items, setItems] = useState<ShoppingItem[] | null>(null)
  const [text, setText] = useState('')
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => { api.shopping().then(setItems).catch((e) => setError(e.message)) }, [])
  useEffect(() => {
    load()
    // Andere Geräte oder Claude können parallel Artikel hinzufügen
    const t = window.setInterval(load, 20000)
    window.addEventListener('focus', load)
    return () => { window.clearInterval(t); window.removeEventListener('focus', load) }
  }, [load])

  const add = async () => {
    if (!text.trim()) return
    try { setItems(await api.addShopping(text)); setText('') } catch (e) { setError((e as Error).message) }
  }
  const toggle = async (i: ShoppingItem) => {
    setItems((xs) => xs?.map((x) => (x.id === i.id ? { ...x, checked: !x.checked } : x)) || null)
    await api.updateShopping(i.id, { checked: !i.checked }).catch(() => {})
    load()
  }
  const remove = async (i: ShoppingItem) => {
    setItems((xs) => xs?.filter((x) => x.id !== i.id) || null)
    await api.deleteShopping(i.id).catch(() => {})
  }

  if (!items) return <div className="py-16 text-center text-slate-500">{error || 'Lade …'}</div>
  const open = items.filter((i) => !i.checked)
  const done = items.filter((i) => i.checked)
  const groups: { label: string; items: ShoppingItem[] }[] = []
  for (const i of open) {
    const g = groups.find((x) => x.label === i.category_label)
    if (g) g.items.push(i)
    else groups.push({ label: i.category_label, items: [i] })
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Einkaufsliste</h1>
        <span className="text-sm text-slate-500">{open.length} offen</span>
      </div>

      <div className="flex gap-2">
        <input className="input" placeholder="z. B. 2 l Milch oder Spülmittel" value={text}
          onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && add()} />
        <button className="btn-primary shrink-0 px-3" onClick={add} aria-label="Hinzufügen"><Plus size={18} /></button>
      </div>
      {error && <p className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">{error}</p>}

      {items.length === 0 && (
        <div className="card px-6 py-12 text-center">
          <ShoppingCart className="mx-auto mb-3 h-10 w-10 text-brand-500" />
          <p className="font-medium">Die Liste ist leer</p>
          <p className="mt-1 text-sm text-slate-500">Im Wochenplan auf „Einkaufsliste“ tippen oder oben etwas eintragen.</p>
        </div>
      )}

      {groups.map((g) => (
        <section key={g.label} className="card px-4 py-2">
          <h2 className="pt-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{g.label}</h2>
          <ul className="divide-y divide-slate-100 dark:divide-slate-800">
            {g.items.map((i) => <Row key={i.id} i={i} onToggle={() => toggle(i)} onDelete={() => remove(i)} />)}
          </ul>
        </section>
      ))}

      {done.length > 0 && (
        <section className="card px-4 py-2">
          <div className="flex items-center justify-between pt-1">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Erledigt ({done.length})</h2>
            <button className="text-xs font-medium text-brand-700 hover:underline dark:text-brand-300"
              onClick={async () => setItems(await api.clearChecked())}>Erledigte entfernen</button>
          </div>
          <ul className="divide-y divide-slate-100 dark:divide-slate-800">
            {done.map((i) => <Row key={i.id} i={i} onToggle={() => toggle(i)} onDelete={() => remove(i)} />)}
          </ul>
        </section>
      )}
    </div>
  )
}
