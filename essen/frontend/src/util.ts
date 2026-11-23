export function cls(...xs: (string | false | null | undefined)[]) {
  return xs.filter(Boolean).join(' ')
}

export const WEEKDAYS = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']

/** ISO-Datum (YYYY-MM-DD) ohne Zeitzonenverschiebung */
export function parseDay(s: string): Date {
  const [y, m, d] = s.split('-').map(Number)
  return new Date(y, m - 1, d)
}

export function isoDay(d: Date): string {
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

export function addDays(s: string, n: number): string {
  const d = parseDay(s)
  d.setDate(d.getDate() + n)
  return isoDay(d)
}

/** 0 = Montag … 6 = Sonntag */
export function weekday(s: string): number {
  return (parseDay(s).getDay() + 6) % 7
}

export function today(): string {
  return isoDay(new Date())
}

export function fmtDay(s: string): string {
  return parseDay(s).toLocaleDateString('de-DE', { weekday: 'long', day: 'numeric', month: 'long' })
}

export function fmtShort(s: string): string {
  return parseDay(s).toLocaleDateString('de-DE', { day: 'numeric', month: 'short' })
}

export function fmtAmount(v: number | null): string {
  if (v === null || v === undefined) return ''
  if (Math.abs(v - Math.round(v)) < 0.01) return String(Math.round(v))
  const whole = Math.floor(v)
  const frac = v - whole
  const sym = Math.abs(frac - 0.5) < 0.01 ? '½' : Math.abs(frac - 0.25) < 0.01 ? '¼' : Math.abs(frac - 0.75) < 0.01 ? '¾' : null
  if (sym) return whole ? `${whole} ${sym}` : sym
  return v.toLocaleString('de-DE', { maximumFractionDigits: 2 })
}

export function fmtMinutes(m: number | null): string {
  if (!m) return ''
  if (m < 60) return `${m} Min.`
  const h = Math.floor(m / 60)
  const r = m % 60
  return r ? `${h} Std. ${r} Min.` : `${h} Std.`
}

/** Haltbarkeits-Farbe nach Frist in Tagen */
export function shelfTone(days: number): string {
  if (days <= 0) return 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300'
  if (days <= 1) return 'bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-300'
  if (days <= 3) return 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'
  return 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
}

export function shelfText(days: number): string {
  if (days >= 99) return 'lange haltbar'
  if (days <= 0) return 'am Abholtag'
  return `bis Tag ${days}`
}

export function gradientFor(s: string): string {
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) % 360
  return `linear-gradient(135deg, hsl(${h} 55% 55%), hsl(${(h + 40) % 360} 60% 42%))`
}

const PLURAL: Record<string, string> = {
  Zehe: 'Zehen', Dose: 'Dosen', Scheibe: 'Scheiben', Stange: 'Stangen', Knolle: 'Knollen', Flasche: 'Flaschen',
  Tasse: 'Tassen', Zweig: 'Zweige', Glas: 'Gläser', Kopf: 'Köpfe', Prise: 'Prisen', Schale: 'Schalen',
}

export function unitText(unit: string, amount: number): string {
  return amount > 1 && PLURAL[unit] ? PLURAL[unit] : unit
}
