import { ArrowLeft, Loader2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api, type Ingredient, type RecipeInput } from '../api'
import { fmtAmount } from '../util'

function ingredientLine(i: Ingredient) {
  const head = [i.amount !== null ? fmtAmount(i.amount) : '', i.unit || '', i.name].filter(Boolean).join(' ')
  return i.note ? `${head}, ${i.note}` : head
}

interface Form {
  title: string
  servings: string
  total_minutes: string
  tags: string
  image_url: string
  source_url: string
  description: string
  ingredients: string
  steps: string
  notes: string
}

const EMPTY: Form = { title: '', servings: '2', total_minutes: '', tags: '', image_url: '', source_url: '', description: '', ingredients: '', steps: '', notes: '' }

export default function RecipeEdit() {
  const { id } = useParams()
  const nav = useNavigate()
  const [f, setF] = useState<Form | null>(id ? null : EMPTY)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    api.recipe(id).then((r) => setF({
      title: r.title,
      servings: String(r.servings),
      total_minutes: r.total_minutes ? String(r.total_minutes) : '',
      tags: r.tags.join(', '),
      image_url: r.image_url || '',
      source_url: r.source_url || '',
      description: r.description || '',
      ingredients: r.ingredients.map(ingredientLine).join('\n'),
      steps: r.steps.join('\n\n'),
      notes: r.notes || '',
    })).catch((e) => setError(e.message))
  }, [id])

  if (!f) return <div className="py-16 text-center text-slate-500">{error || 'Lade …'}</div>
  const set = (k: keyof Form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setF({ ...f, [k]: e.target.value })

  const save = async () => {
    setBusy(true); setError(null)
    const body: RecipeInput = {
      title: f.title.trim(),
      servings: Math.max(1, Number(f.servings) || 2),
      total_minutes: f.total_minutes ? Number(f.total_minutes) : null,
      tags: f.tags.split(',').map((t) => t.trim()).filter(Boolean),
      image_url: f.image_url.trim() || null,
      source_url: f.source_url.trim() || null,
      description: f.description.trim() || null,
      ingredients_text: f.ingredients,
      steps: f.steps.split(/\n\s*\n|\n/).map((s) => s.trim()).filter(Boolean),
      notes: f.notes.trim() || null,
    }
    try {
      const r = id ? await api.updateRecipe(id, body) : await api.createRecipe(body)
      nav(`/rezepte/${r.id}`, { replace: true })
    } catch (e) {
      setError((e as Error).message)
    } finally { setBusy(false) }
  }

  return (
    <div className="space-y-4">
      <button className="btn-ghost -ml-3" onClick={() => nav(-1)}><ArrowLeft size={16} /> Zurück</button>
      <h1 className="text-2xl font-bold">{id ? 'Rezept bearbeiten' : 'Neues Rezept'}</h1>
      <div className="card space-y-4 p-4 sm:p-6">
        <div>
          <label className="label" htmlFor="title">Titel</label>
          <input id="title" className="input" value={f.title} onChange={set('title')} autoFocus={!id} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label" htmlFor="servings">Portionen</label>
            <input id="servings" type="number" min={1} className="input" value={f.servings} onChange={set('servings')} />
          </div>
          <div>
            <label className="label" htmlFor="minutes">Zeit gesamt (Min.)</label>
            <input id="minutes" type="number" min={0} className="input" value={f.total_minutes} onChange={set('total_minutes')} />
          </div>
        </div>
        <div>
          <label className="label" htmlFor="tags">Schlagworte (mit Komma getrennt)</label>
          <input id="tags" className="input" placeholder="Vegetarisch, Schnell, Familienliebling" value={f.tags} onChange={set('tags')} />
        </div>
        <div>
          <label className="label" htmlFor="ing">Zutaten (eine pro Zeile)</label>
          <textarea id="ing" rows={8} className="input font-mono text-[13px]" placeholder={'500 g Hackfleisch\n1 Zwiebel\n1 Dose Tomaten, stückig'} value={f.ingredients} onChange={set('ingredients')} />
          <p className="mt-1 text-xs text-slate-500">Menge, Einheit und Kategorie werden automatisch erkannt.</p>
        </div>
        <div>
          <label className="label" htmlFor="steps">Zubereitung (ein Schritt pro Zeile)</label>
          <textarea id="steps" rows={8} className="input" value={f.steps} onChange={set('steps')} />
        </div>
        <div>
          <label className="label" htmlFor="desc">Kurzbeschreibung</label>
          <input id="desc" className="input" value={f.description} onChange={set('description')} />
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="img">Bild-Link</label>
            <input id="img" className="input" value={f.image_url} onChange={set('image_url')} />
          </div>
          <div>
            <label className="label" htmlFor="src">Quelle</label>
            <input id="src" className="input" value={f.source_url} onChange={set('source_url')} />
          </div>
        </div>
        <div>
          <label className="label" htmlFor="notes">Notizen</label>
          <textarea id="notes" rows={3} className="input" value={f.notes} onChange={set('notes')} />
        </div>
        {error && <p className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">{error}</p>}
        <div className="flex justify-end gap-2">
          <button className="btn-ghost" onClick={() => nav(-1)}>Abbrechen</button>
          <button className="btn-primary" disabled={busy || !f.title.trim()} onClick={save}>
            {busy && <Loader2 size={16} className="animate-spin" />} Speichern
          </button>
        </div>
      </div>
    </div>
  )
}
