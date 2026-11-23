import { AlertTriangle, Check, ChevronLeft, ChevronRight, Clock, Loader2, Minus, Plus, Shuffle, ShoppingBag, ShoppingCart, Sparkles, Trash2, Users } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, type Plan, type PlanEntry } from '../api'
import RecipePicker from '../components/RecipePicker'
import Stars from '../components/Stars'
import { addDays, cls, fmtMinutes, fmtShort, parseDay, today, weekday, WEEKDAYS } from '../util'

function EntryRow({ e, onChange, onDelete, onSwap }: {
  e: PlanEntry
  onChange: (p: Partial<PlanEntry>) => void
  onDelete: () => void
  onSwap: () => void
}) {
  const [rate, setRate] = useState(false)
  const title = e.recipe_title || e.title || 'Ohne Titel'
  const content = (
    <>
      <div className="h-12 w-12 shrink-0 overflow-hidden rounded-xl bg-slate-100 dark:bg-slate-800">
        {e.recipe_image && <img src={e.recipe_image} alt="" className="h-full w-full object-cover" referrerPolicy="no-referrer" />}
      </div>
      <div className="min-w-0 flex-1">
        <p className={cls('truncate font-medium', e.cooked && 'text-slate-400 line-through')}>{title}</p>
        <p className="flex items-center gap-2 text-xs text-slate-500">
          {e.recipe_minutes ? <span className="inline-flex items-center gap-1"><Clock size={12} />{fmtMinutes(e.recipe_minutes)}</span> : null}
          {!e.recipe_id && <span>ohne Rezept</span>}
        </p>
      </div>
    </>
  )
  return (
    <div className="py-2">
      <div className="flex items-center gap-3">
        {e.recipe_id ? <Link to={`/rezepte/${e.recipe_id}?portionen=${e.servings}`} className="flex min-w-0 flex-1 items-center gap-3">{content}</Link>
          : <div className="flex min-w-0 flex-1 items-center gap-3">{content}</div>}
        <div className="flex shrink-0 items-center">
          <span className="mr-1 hidden items-center gap-0.5 text-xs text-slate-500 sm:inline-flex">
            <button className="icon-btn h-7 w-7" onClick={() => onChange({ servings: Math.max(1, e.servings - 1) })} aria-label="Weniger Portionen"><Minus size={14} /></button>
            <Users size={12} />{e.servings}
            <button className="icon-btn h-7 w-7" onClick={() => onChange({ servings: e.servings + 1 })} aria-label="Mehr Portionen"><Plus size={14} /></button>
          </span>
          {e.recipe_id && !e.cooked && <button className="icon-btn" onClick={onSwap} title="Anderes Gericht"><Shuffle size={17} /></button>}
          <button className={cls('icon-btn', e.cooked && 'text-brand-600')} title={e.cooked ? 'Nicht gekocht' : 'Gekocht'}
            onClick={() => { onChange({ cooked: !e.cooked }); if (!e.cooked && e.recipe_id) setRate(true) }}>
            <Check size={18} />
          </button>
          <button className="icon-btn" onClick={onDelete} title="Entfernen"><Trash2 size={17} /></button>
        </div>
      </div>
      {rate && e.recipe_id && (
        <div className="mt-2 flex items-center gap-3 rounded-xl bg-brand-50 px-3 py-2 text-sm dark:bg-brand-900/30">
          <span>Wie hat's geschmeckt?</span>
          <Stars value={null} size={20} onRate={(n) => { api.rate(e.recipe_id!, n).finally(() => setRate(false)) }} />
          <button className="ml-auto text-xs text-slate-500" onClick={() => setRate(false)}>Später</button>
        </div>
      )}
    </div>
  )
}

export default function PlanPage() {
  const nav = useNavigate()
  const [plan, setPlan] = useState<Plan | null>(null)
  const [start, setStart] = useState<string | undefined>(undefined)
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [hint, setHint] = useState<string | null>(null)
  const [picker, setPicker] = useState<{ day: string; slot: string } | null>(null)

  const load = useCallback(() => {
    api.plan(start).then((p) => { setPlan(p); setError(null) }).catch((e) => setError(e.message))
  }, [start])
  useEffect(load, [load])

  if (!plan) return <div className="py-16 text-center text-slate-500">{error || 'Lade …'}</div>

  const days = Array.from({ length: plan.days }, (_, i) => addDays(plan.start, i))
  const offsetOf = (d: string) => (weekday(d) - plan.pickup_weekday + 7) % 7
  const end = days[days.length - 1]
  const t = today()

  const run = async (key: string, fn: () => Promise<unknown>) => {
    setBusy(key); setError(null); setHint(null)
    try { await fn() } catch (e) { setError((e as Error).message) } finally { setBusy(null) }
  }

  const generate = (replace: boolean) => run(replace ? 'regen' : 'gen', async () => {
    const p = await api.generate(plan.start, plan.days, replace)
    setPlan(p)
    const free = days.filter((d) => d >= t).length * p.slots.length -
      p.entries.filter((e) => e.day >= t && p.slots.some((s) => s.key === e.slot)).length
    if (free > 0) setHint(`${free} ${free === 1 ? 'Platz blieb' : 'Plätze blieben'} frei: Es gibt nicht genug passende Rezepte (Haltbarkeit, Abwechslung oder Ausschlüsse). Mehr Rezepte anlegen oder selbst etwas eintragen.`)
  })

  const update = (e: PlanEntry, p: Partial<PlanEntry>) => run('u' + e.id, async () => { await api.updateEntry(e.id, p); load() })
  const remove = (e: PlanEntry) => run('d' + e.id, async () => { await api.deleteEntry(e.id); load() })
  const swap = (e: PlanEntry) => run('s' + e.id, async () => { await api.swapEntry(e.id); load() })

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Wochenplan</h1>
          <div className="mt-1 flex items-center gap-1 text-sm text-slate-500">
            <button className="icon-btn h-8 w-8" onClick={() => setStart(addDays(plan.start, -plan.days))} aria-label="Vorherige Woche"><ChevronLeft size={18} /></button>
            <span>{fmtShort(plan.start)} – {fmtShort(end)}</span>
            <button className="icon-btn h-8 w-8" onClick={() => setStart(addDays(plan.start, plan.days))} aria-label="Nächste Woche"><ChevronRight size={18} /></button>
          </div>
        </div>
        <div className="grid w-full grid-cols-3 gap-2 sm:flex sm:w-auto">
          <button className="btn-primary px-2 sm:px-4" disabled={!!busy} onClick={() => generate(false)}>
            {busy === 'gen' ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />} Füllen
          </button>
          <button className="btn-outline px-2 sm:px-4" disabled={!!busy} onClick={() => generate(true)} title="Alle noch nicht gekochten Gerichte neu würfeln">
            {busy === 'regen' ? <Loader2 size={16} className="animate-spin" /> : <Shuffle size={16} />} Würfeln
          </button>
          <button className="btn-outline px-2 sm:px-4" disabled={!!busy || plan.entries.length === 0}
            onClick={() => run('shop', async () => { await api.shoppingFromPlan(plan.start, plan.days); nav('/einkauf') })}>
            <ShoppingCart size={16} /> Einkauf
          </button>
        </div>
      </div>

      {error && <div className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">{error}</div>}
      {hint && <div className="rounded-xl bg-sky-50 px-4 py-3 text-sm text-sky-800 dark:bg-sky-950 dark:text-sky-200">{hint}</div>}
      {plan.warnings.length > 0 && (
        <div className="space-y-1 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:bg-amber-950 dark:text-amber-200">
          {plan.warnings.map((w) => <p key={w.entry_id} className="flex gap-2"><AlertTriangle size={16} className="mt-0.5 shrink-0" />{w.message}</p>)}
        </div>
      )}

      <div className="space-y-3">
        {days.map((d) => {
          const isPickup = weekday(d) === plan.pickup_weekday
          const past = d < t
          const dayEntries = plan.entries.filter((e) => e.day === d)
          const slotKeys = [...plan.slots.map((s) => s.key), ...dayEntries.map((e) => e.slot).filter((k) => !plan.slots.some((s) => s.key === k))]
          return (
            <section key={d} className={cls('card px-4 py-3', past && 'opacity-70', d === t && 'ring-2 ring-brand-500/60')}>
              <div className="mb-1 flex items-center gap-2">
                <h2 className="font-semibold">{WEEKDAYS[weekday(d)]}</h2>
                <span className="text-sm text-slate-500">{parseDay(d).toLocaleDateString('de-DE', { day: 'numeric', month: 'short' })}</span>
                {d === t && <span className="chip bg-brand-100 text-brand-800 dark:bg-brand-900 dark:text-brand-100">Heute</span>}
                {isPickup && <span className="chip bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-200"><ShoppingBag size={12} /> Abholung</span>}
              </div>
              {[...new Set(slotKeys)].map((key) => {
                const label = plan.slots.find((s) => s.key === key)?.label || key
                const es = dayEntries.filter((e) => e.slot === key)
                return (
                  <div key={key} className="border-t border-slate-100 pt-1 first:border-t-0 dark:border-slate-800">
                    {plan.slots.length > 1 && <p className="pt-1 text-xs font-medium uppercase tracking-wide text-slate-400">{label}</p>}
                    <div className="divide-y divide-slate-100 dark:divide-slate-800">
                      {es.map((e) => (
                        <EntryRow key={e.id} e={e} onChange={(p) => update(e, p)} onDelete={() => remove(e)} onSwap={() => swap(e)} />
                      ))}
                    </div>
                    {es.length === 0 && (
                      <button className="my-1 flex w-full items-center gap-2 rounded-xl border border-dashed border-slate-200 px-3 py-3 text-sm text-slate-500 hover:border-brand-400 hover:text-brand-700 dark:border-slate-700"
                        onClick={() => setPicker({ day: d, slot: key })}>
                        <Plus size={16} /> Gericht eintragen
                      </button>
                    )}
                  </div>
                )
              })}
            </section>
          )
        })}
      </div>

      <RecipePicker
        open={!!picker}
        title={picker ? `${WEEKDAYS[weekday(picker.day)]}, ${fmtShort(picker.day)}` : ''}
        offset={picker ? offsetOf(picker.day) : undefined}
        onClose={() => setPicker(null)}
        onPick={(c) => {
          const p = picker!
          setPicker(null)
          run('add', async () => { await api.addEntry({ day: p.day, slot: p.slot, ...c }); load() })
        }}
      />
    </div>
  )
}
