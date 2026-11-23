import { BookOpen, Clock, Heart, Link2, Loader2, Plus, Search } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, type Recipe } from '../api'
import Modal from '../components/Modal'
import Stars from '../components/Stars'
import { cls, fmtMinutes, gradientFor, shelfText, shelfTone } from '../util'

function Card({ r }: { r: Recipe }) {
  const minutes = r.total_minutes || r.prep_minutes
  return (
    <Link to={`/rezepte/${r.id}`} className="card group block overflow-hidden transition hover:-translate-y-0.5 hover:shadow-xl">
      <div className="relative h-36 overflow-hidden" style={r.image_url ? undefined : { background: gradientFor(r.title) }}>
        {r.image_url
          ? <img src={r.image_url} alt="" loading="lazy" referrerPolicy="no-referrer" className="h-full w-full object-cover transition duration-500 group-hover:scale-105" />
          : <BookOpen className="absolute -bottom-3 -right-3 h-24 w-24 rotate-12 text-white/25" />}
        {r.favorite && <Heart size={18} className="absolute right-3 top-3 fill-rose-500 text-rose-500 drop-shadow" />}
      </div>
      <div className="space-y-1.5 p-3">
        <h3 className="line-clamp-2 font-semibold leading-snug">{r.title}</h3>
        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
          {minutes ? <span className="inline-flex items-center gap-1"><Clock size={12} />{fmtMinutes(minutes)}</span> : null}
          {r.rating !== null && <Stars value={r.rating} size={12} />}
          {r.deadline_days < 99 && <span className={cls('chip', shelfTone(r.deadline_days))}>{shelfText(r.deadline_days)}</span>}
        </div>
      </div>
    </Link>
  )
}

export default function RecipesPage() {
  const nav = useNavigate()
  const [recipes, setRecipes] = useState<Recipe[] | null>(null)
  const [q, setQ] = useState('')
  const [tag, setTag] = useState<string | null>(null)
  const [importOpen, setImportOpen] = useState(false)
  const [url, setUrl] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => { api.recipes().then(setRecipes).catch((e) => setError(e.message)) }, [])

  const tags = useMemo(() => {
    const c = new Map<string, number>()
    recipes?.forEach((r) => r.tags.forEach((t) => c.set(t, (c.get(t) || 0) + 1)))
    return [...c.entries()].sort((a, b) => b[1] - a[1]).slice(0, 14).map(([t]) => t)
  }, [recipes])

  const list = useMemo(() => {
    const ql = q.trim().toLowerCase()
    return (recipes || []).filter((r) =>
      (!tag || r.tags.includes(tag)) &&
      (!ql || r.title.toLowerCase().includes(ql) || r.ingredients.some((i) => i.name.toLowerCase().includes(ql))))
  }, [recipes, q, tag])

  const doImport = async () => {
    setBusy(true); setError(null)
    try {
      const r = await api.importRecipe(url.trim())
      setImportOpen(false); setUrl('')
      nav(`/rezepte/${r.id}`)
    } catch (e) {
      setError((e as Error).message)
    } finally { setBusy(false) }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Rezepte</h1>
        <div className="flex gap-2">
          <button className="btn-outline" onClick={() => { setError(null); setImportOpen(true) }}><Link2 size={16} /> Per Link</button>
          <Link to="/rezepte/neu" className="btn-primary"><Plus size={16} /> Neu</Link>
        </div>
      </div>

      <div className="relative">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <input className="input pl-9" placeholder="Rezept oder Zutat suchen …" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>
      {tags.length > 0 && (
        <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1">
          {tags.map((t) => (
            <button key={t} onClick={() => setTag(tag === t ? null : t)}
              className={cls('chip shrink-0 py-1', tag === t ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200')}>
              {t}
            </button>
          ))}
        </div>
      )}

      {recipes === null ? <p className="py-12 text-center text-slate-500">Lade …</p>
        : recipes.length === 0 ? (
          <div className="card px-6 py-12 text-center">
            <BookOpen className="mx-auto mb-3 h-10 w-10 text-brand-500" />
            <p className="font-medium">Noch keine Rezepte</p>
            <p className="mt-1 text-sm text-slate-500">Füg einen Link von Chefkoch, REWE & Co. ein, leg selbst eins an oder bitte Claude darum.</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {list.map((r) => <Card key={r.id} r={r} />)}
          </div>
        )}

      <Modal open={importOpen} onClose={() => setImportOpen(false)} title="Rezept per Link importieren"
        footer={<>
          <button className="btn-ghost" onClick={() => setImportOpen(false)}>Abbrechen</button>
          <button className="btn-primary" disabled={busy || url.trim().length < 8} onClick={doImport}>
            {busy && <Loader2 size={16} className="animate-spin" />} Importieren
          </button>
        </>}>
        <label className="label" htmlFor="url">Link zum Rezept</label>
        <input id="url" className="input" placeholder="https://www.chefkoch.de/rezepte/…" value={url} autoFocus
          onChange={(e) => setUrl(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && url.trim().length >= 8 && doImport()} />
        <p className="mt-2 text-xs text-slate-500">Funktioniert mit den meisten Rezeptseiten (Chefkoch, REWE, Lecker, EatSmarter …). Zutaten und Schritte kannst du danach anpassen.</p>
        {error && <p className="mt-3 rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">{error}</p>}
      </Modal>
    </div>
  )
}
