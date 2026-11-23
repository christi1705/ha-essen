import { ArrowLeft, CalendarPlus, ChefHat, ChevronLeft, ChevronRight, Clock, ExternalLink, Heart, ListChecks, Minus, Pencil, Plus, Trash2, Users, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { api, type Ingredient, type Recipe, type Settings } from '../api'
import Modal from '../components/Modal'
import Stars from '../components/Stars'
import { useInfo } from '../info'
import { addDays, cls, fmtAmount, unitText, fmtMinutes, fmtShort, shelfText, shelfTone, today, weekday, WEEKDAYS } from '../util'

function scaled(i: Ingredient, f: number) {
  const a = i.amount !== null ? fmtAmount(i.amount * f) : ''
  return [a, i.unit ? unitText(i.unit, i.amount !== null ? i.amount * f : 1) : ''].filter(Boolean).join(' ')
}

function CookMode({ r, factor, onClose }: { r: Recipe; factor: number; onClose: () => void }) {
  const [i, setI] = useState(0)
  const [showIng, setShowIng] = useState(false)
  useEffect(() => {
    // Bildschirm beim Kochen anlassen
    let lock: { release: () => Promise<void> } | null = null
    const nav = navigator as Navigator & { wakeLock?: { request: (t: 'screen') => Promise<{ release: () => Promise<void> }> } }
    nav.wakeLock?.request('screen').then((l) => { lock = l }).catch(() => {})
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') setI((x) => Math.min(x + 1, r.steps.length - 1))
      if (e.key === 'ArrowLeft') setI((x) => Math.max(x - 1, 0))
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => { window.removeEventListener('keydown', onKey); lock?.release().catch(() => {}) }
  }, [r.steps.length, onClose])
  const n = r.steps.length
  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-white dark:bg-slate-950">
      <div className="flex items-center gap-2 border-b border-slate-100 px-4 py-3 dark:border-slate-800">
        <button className="icon-btn" onClick={onClose} aria-label="Schließen"><X size={20} /></button>
        <p className="min-w-0 flex-1 truncate font-semibold">{r.title}</p>
        <button className={cls('btn-outline', showIng && 'bg-brand-50')} onClick={() => setShowIng(!showIng)}><ListChecks size={16} /> Zutaten</button>
      </div>
      {showIng ? (
        <ul className="flex-1 overflow-y-auto px-6 py-4 text-lg">
          {r.ingredients.map((x, k) => (
            <li key={k} className="flex gap-3 border-b border-slate-100 py-2 dark:border-slate-800">
              <span className="w-28 shrink-0 text-right font-semibold tabular-nums">{scaled(x, factor)}</span>
              <span>{x.name}{x.note && <span className="text-slate-500">, {x.note}</span>}</span>
            </li>
          ))}
        </ul>
      ) : (
        <div className="flex flex-1 flex-col justify-center overflow-y-auto px-6 py-8 sm:px-16">
          {n === 0 ? <p className="text-center text-slate-500">Dieses Rezept hat keine Schritte.</p> : <>
            <p className="mb-4 text-sm font-semibold uppercase tracking-wide text-brand-600">Schritt {i + 1} von {n}</p>
            <p className="text-2xl leading-relaxed sm:text-3xl">{r.steps[i]}</p>
          </>}
        </div>
      )}
      <div className="flex items-center gap-3 border-t border-slate-100 px-4 py-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] dark:border-slate-800">
        <button className="btn-outline flex-1 py-3" disabled={i === 0} onClick={() => setI(i - 1)}><ChevronLeft size={18} /> Zurück</button>
        {i < n - 1
          ? <button className="btn-primary flex-1 py-3" onClick={() => setI(i + 1)}>Weiter <ChevronRight size={18} /></button>
          : <button className="btn-primary flex-1 py-3" onClick={onClose}>Fertig</button>}
      </div>
    </div>
  )
}

export default function RecipeDetail() {
  const { id } = useParams()
  const [sp] = useSearchParams()
  const nav = useNavigate()
  const { info } = useInfo()
  const [r, setR] = useState<Recipe | null>(null)
  const [servings, setServings] = useState<number | null>(null)
  const [cook, setCook] = useState(false)
  const [planOpen, setPlanOpen] = useState(false)
  const [settings, setSettings] = useState<Settings | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)

  useEffect(() => {
    api.recipe(id!).then((x) => {
      setR(x)
      const p = Number(sp.get('portionen'))
      setServings(p > 0 ? p : x.servings)
    }).catch((e) => setError(e.message))
  }, [id, sp])

  if (!r || servings === null) return <div className="py-16 text-center text-slate-500">{error || 'Lade …'}</div>
  const factor = servings / r.servings
  const cats = info?.categories || []

  const setCategory = async (idx: number, category: string) => {
    const ingredients = r.ingredients.map((x, k) => (k === idx ? { ...x, category } : x))
    setR(await api.updateRecipe(r.id, { ingredients }))
  }

  const openPlan = async () => {
    setPlanOpen(true)
    if (!settings) setSettings(await api.settings())
  }
  const addToPlan = async (day: string, slot: string) => {
    await api.addEntry({ day, slot, recipe_id: r.id, servings })
    setPlanOpen(false)
    setMsg(`Für ${WEEKDAYS[weekday(day)]}, ${fmtShort(day)} eingeplant.`)
  }

  const slots = settings?.slots.filter((s) => s.enabled) || []
  const minutes = r.total_minutes || r.prep_minutes

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-2">
        <button className="btn-ghost -ml-3" onClick={() => nav(-1)}><ArrowLeft size={16} /> Zurück</button>
        <div className="flex">
          <button className="icon-btn" title={r.favorite ? 'Kein Favorit' : 'Favorit'}
            onClick={async () => setR(await api.updateRecipe(r.id, { favorite: !r.favorite }))}>
            <Heart size={18} className={cls(r.favorite && 'fill-rose-500 text-rose-500')} />
          </button>
          <Link to={`/rezepte/${r.id}/bearbeiten`} className="icon-btn" title="Bearbeiten"><Pencil size={18} /></Link>
          <button className="icon-btn" title="Löschen" onClick={async () => {
            if (confirm(`„${r.title}“ löschen?`)) { await api.deleteRecipe(r.id); nav('/rezepte') }
          }}><Trash2 size={18} /></button>
        </div>
      </div>

      {r.image_url && <img src={r.image_url} alt="" referrerPolicy="no-referrer" className="h-56 w-full rounded-3xl object-cover sm:h-72" />}

      <div>
        <h1 className="text-2xl font-bold leading-tight sm:text-3xl">{r.title}</h1>
        {r.description && <p className="mt-2 text-slate-600 dark:text-slate-300">{r.description}</p>}
        <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-slate-500">
          {minutes ? <span className="inline-flex items-center gap-1"><Clock size={14} />{fmtMinutes(minutes)}</span> : null}
          <span className="inline-flex items-center gap-1"><Stars value={r.rating} size={16} onRate={async (n) => setR(await api.rate(r.id, n))} />
            {r.rating_count > 0 && <span className="text-xs">({r.rating_count})</span>}</span>
          {r.deadline_days < 99 && <span className={cls('chip', shelfTone(r.deadline_days))}>Frisch kochen: {shelfText(r.deadline_days)}</span>}
          {r.source_url && <a href={r.source_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 hover:text-brand-700"><ExternalLink size={14} />Quelle</a>}
        </div>
        {r.tags.length > 0 && <div className="mt-3 flex flex-wrap gap-1.5">{r.tags.map((t) => <span key={t} className="chip bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200">{t}</span>)}</div>}
      </div>

      <div className="flex flex-wrap gap-2">
        <button className="btn-primary" onClick={() => setCook(true)}><ChefHat size={16} /> Kochmodus</button>
        <button className="btn-outline" onClick={openPlan}><CalendarPlus size={16} /> Einplanen</button>
      </div>
      {msg && <p className="rounded-xl bg-brand-50 px-4 py-2 text-sm text-brand-800 dark:bg-brand-900/40 dark:text-brand-100">{msg}</p>}

      <div className="grid grid-cols-1 gap-5 md:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        <section className="card p-4">
          <div className="mb-2 flex items-center justify-between">
            <h2 className="font-semibold">Zutaten</h2>
            <span className="inline-flex items-center gap-1 text-sm">
              <button className="icon-btn h-8 w-8" onClick={() => setServings(Math.max(1, servings - 1))} aria-label="Weniger"><Minus size={14} /></button>
              <Users size={14} /> {servings}
              <button className="icon-btn h-8 w-8" onClick={() => setServings(servings + 1)} aria-label="Mehr"><Plus size={14} /></button>
            </span>
          </div>
          <ul className="divide-y divide-slate-100 dark:divide-slate-800">
            {r.ingredients.map((x, k) => (
              <li key={k} className="flex items-start gap-3 py-2 text-sm">
                <span className="w-20 shrink-0 text-right font-medium tabular-nums">{scaled(x, factor)}</span>
                <div className="min-w-0 flex-1">
                  <p>{x.name}{x.note && <span className="text-slate-500">, {x.note}</span>}</p>
                  <select className="mt-0.5 w-full min-w-0 truncate bg-transparent text-xs text-slate-400 outline-none hover:text-slate-600"
                    value={x.category || 'sonstiges'} onChange={(e) => setCategory(k, e.target.value)} title="Kategorie (bestimmt Haltbarkeit und Sortierung)">
                    {cats.map((c) => <option key={c.key} value={c.key}>{c.label}{c.shelf_days < 99 ? ` · ${shelfText(c.shelf_days)}` : ''}</option>)}
                  </select>
                </div>
              </li>
            ))}
            {r.ingredients.length === 0 && <li className="py-3 text-sm text-slate-500">Keine Zutaten eingetragen</li>}
          </ul>
        </section>
        <section className="card p-4">
          <h2 className="mb-2 font-semibold">Zubereitung</h2>
          <ol className="space-y-3">
            {r.steps.map((s, k) => (
              <li key={k} className="flex gap-3 text-sm leading-relaxed">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-100 text-xs font-bold text-brand-800 dark:bg-brand-900 dark:text-brand-100">{k + 1}</span>
                <span>{s}</span>
              </li>
            ))}
            {r.steps.length === 0 && <li className="text-sm text-slate-500">Keine Schritte eingetragen</li>}
          </ol>
          {r.notes && <p className="mt-4 whitespace-pre-line rounded-xl bg-slate-50 p-3 text-sm dark:bg-slate-800">{r.notes}</p>}
        </section>
      </div>

      {cook && <CookMode r={r} factor={factor} onClose={() => setCook(false)} />}

      <Modal open={planOpen} onClose={() => setPlanOpen(false)} title="Einplanen">
        {!settings ? <p className="text-sm text-slate-500">Lade …</p> : (
          <ul className="divide-y divide-slate-100 dark:divide-slate-800">
            {Array.from({ length: 14 }, (_, k) => addDays(today(), k)).map((d) => {
              const offset = (weekday(d) - settings.pickup_weekday + 7) % 7
              const late = r.deadline_days < offset
              return (
                <li key={d} className="flex items-center gap-2 py-2">
                  <span className="flex-1 text-sm">
                    {WEEKDAYS[weekday(d)]}, {fmtShort(d)}
                    {late && <span className="ml-2 text-xs text-red-600">zu spät nach dem Einkauf</span>}
                  </span>
                  {slots.map((s) => (
                    <button key={s.key} className="btn-outline px-3 py-1.5" onClick={() => addToPlan(d, s.key)}>{slots.length > 1 ? s.label : 'Hinzufügen'}</button>
                  ))}
                </li>
              )
            })}
          </ul>
        )}
      </Modal>
    </div>
  )
}
