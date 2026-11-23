import { Check, Loader2 } from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { api, type Settings } from '../api'
import { useInfo } from '../info'
import { cls, WEEKDAYS } from '../util'

function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <div>
      <span className="label">{label}</span>
      {children}
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  )
}

const listText = (xs: string[]) => xs.join(', ')
const textList = (s: string) => s.split(',').map((x) => x.trim()).filter(Boolean)

export default function SettingsPage() {
  const { info, reload } = useInfo()
  const [s, setS] = useState<Settings | null>(null)
  const [lists, setLists] = useState({ exclude_ingredients: '', exclude_tags: '', prefer_tags: '', pantry_staples: '' })
  const [busy, setBusy] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.settings().then((x) => {
      setS(x)
      setLists({
        exclude_ingredients: listText(x.exclude_ingredients), exclude_tags: listText(x.exclude_tags),
        prefer_tags: listText(x.prefer_tags), pantry_staples: listText(x.pantry_staples),
      })
    }).catch((e) => setError(e.message))
  }, [])

  if (!s) return <div className="py-16 text-center text-slate-500">{error || 'Lade …'}</div>
  const up = (p: Partial<Settings>) => { setS({ ...s, ...p }); setSaved(false) }
  const upList = (k: keyof typeof lists) => (e: React.ChangeEvent<HTMLInputElement>) => { setLists({ ...lists, [k]: e.target.value }); setSaved(false) }

  const save = async () => {
    setBusy(true); setError(null)
    try {
      const res = await api.saveSettings({
        ...s,
        exclude_ingredients: textList(lists.exclude_ingredients),
        exclude_tags: textList(lists.exclude_tags),
        prefer_tags: textList(lists.prefer_tags),
        pantry_staples: textList(lists.pantry_staples),
      })
      setS(res); setSaved(true); reload()
    } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Einstellungen</h1>

      <section className="card space-y-4 p-4 sm:p-6">
        <h2 className="font-semibold">Haushalt & Woche</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="Personen" hint="Standard-Portionen pro Mahlzeit">
            <input type="number" min={1} max={20} className="input" value={s.persons} onChange={(e) => up({ persons: Number(e.target.value) || 1 })} />
          </Field>
          <Field label="Abholtag" hint="Ab diesem Tag zählt die Haltbarkeit">
            <select className="input" value={s.pickup_weekday} onChange={(e) => up({ pickup_weekday: Number(e.target.value) })}>
              {WEEKDAYS.map((d, i) => <option key={d} value={i}>{d}</option>)}
            </select>
          </Field>
          <Field label="Tage pro Plan">
            <input type="number" min={1} max={14} className="input" value={s.plan_days} onChange={(e) => up({ plan_days: Number(e.target.value) || 7 })} />
          </Field>
        </div>
        <Field label="Mahlzeiten">
          <div className="flex flex-wrap gap-2">
            {s.slots.map((sl, i) => (
              <button key={sl.key} onClick={() => up({ slots: s.slots.map((x, k) => (k === i ? { ...x, enabled: !x.enabled } : x)) })}
                className={cls('chip py-1.5 text-sm', sl.enabled ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300')}>
                {sl.enabled && <Check size={14} />} {sl.label}
              </button>
            ))}
          </div>
        </Field>
      </section>

      <section className="card space-y-4 p-4 sm:p-6">
        <h2 className="font-semibold">Vorlieben</h2>
        <Field label="Zutaten ausschließen" hint="Rezepte mit diesen Zutaten werden nicht vorgeschlagen (mit Komma getrennt)">
          <input className="input" placeholder="z. B. Rosinen, Koriander" value={lists.exclude_ingredients} onChange={upList('exclude_ingredients')} />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Bevorzugte Schlagworte">
            <input className="input" placeholder="z. B. Schnell, Vegetarisch" value={lists.prefer_tags} onChange={upList('prefer_tags')} />
          </Field>
          <Field label="Schlagworte ausschließen">
            <input className="input" placeholder="z. B. Dessert" value={lists.exclude_tags} onChange={upList('exclude_tags')} />
          </Field>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Nicht wiederholen innerhalb von (Tagen)">
            <input type="number" min={0} max={90} className="input" value={s.repeat_block_days} onChange={(e) => up({ repeat_block_days: Number(e.target.value) || 0 })} />
          </Field>
          <Field label="Immer im Haus" hint="Kommt nicht auf die Einkaufsliste">
            <input className="input" value={lists.pantry_staples} onChange={upList('pantry_staples')} />
          </Field>
        </div>
      </section>

      <section className="card p-4 sm:p-6">
        <h2 className="font-semibold">Haltbarkeit nach der Abholung</h2>
        <p className="mb-3 mt-1 text-sm text-slate-500">Spätestens am wievielten Tag nach dem Einkauf verbraucht werden muss (0 = am Abholtag, 99 = egal).</p>
        <div className="divide-y divide-slate-100 dark:divide-slate-800">
          {(info?.categories || []).map((c) => (
            <label key={c.key} className="flex items-center gap-3 py-2 text-sm">
              <span className="flex-1">{c.label}</span>
              <input type="number" min={0} max={99} className="input w-20 text-right" placeholder={String(c.default_shelf_days)}
                value={s.shelf_days[c.key] ?? ''}
                onChange={(e) => {
                  const v = e.target.value
                  const next = { ...s.shelf_days }
                  if (v === '') delete next[c.key]
                  else next[c.key] = Number(v)
                  up({ shelf_days: next })
                }} />
            </label>
          ))}
        </div>
      </section>

      {error && <p className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">{error}</p>}
      <div className="sticky bottom-20 flex justify-end sm:bottom-4">
        <button className="btn-primary shadow-lg" disabled={busy} onClick={save}>
          {busy ? <Loader2 size={16} className="animate-spin" /> : saved ? <Check size={16} /> : null} {saved ? 'Gespeichert' : 'Speichern'}
        </button>
      </div>
      {info && <p className="text-center text-xs text-slate-400">Essen {info.version}</p>}
    </div>
  )
}
