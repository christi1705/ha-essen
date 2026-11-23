// API-Zugriff – immer relative Pfade, damit HA Ingress funktioniert.

export interface Ingredient {
  amount: number | null
  unit: string | null
  name: string
  note: string | null
  category: string | null
}

export interface Recipe {
  id: string
  title: string
  description: string | null
  source_url: string | null
  image_url: string | null
  servings: number
  prep_minutes: number | null
  total_minutes: number | null
  tags: string[]
  ingredients: Ingredient[]
  steps: string[]
  notes: string | null
  favorite: boolean
  archived: boolean
  rating: number | null
  rating_count: number
  last_cooked: string | null
  deadline_days: number
  deadline_category: string | null
}

export type RecipeInput = Partial<Omit<Recipe, 'id' | 'rating' | 'rating_count' | 'last_cooked' | 'deadline_days' | 'deadline_category'>> & {
  ingredients_text?: string
}

export interface Category {
  key: string
  label: string
  shelf_days: number
  default_shelf_days: number
}

export interface AppInfo {
  version: string
  user: string | null
  categories: Category[]
}

export interface Slot {
  key: string
  label: string
  enabled: boolean
}

export interface Settings {
  persons: number
  slots: Slot[]
  pickup_weekday: number
  plan_days: number
  exclude_ingredients: string[]
  exclude_tags: string[]
  prefer_tags: string[]
  repeat_block_days: number
  pantry_staples: string[]
  shelf_days: Record<string, number>
}

export interface PlanEntry {
  id: string
  day: string
  slot: string
  recipe_id: string | null
  title: string | null
  servings: number
  note: string | null
  cooked: boolean
  recipe_title: string | null
  recipe_image: string | null
  recipe_minutes: number | null
}

export interface Plan {
  start: string
  days: number
  pickup_weekday: number
  slots: Slot[]
  entries: PlanEntry[]
  warnings: { entry_id: string; day: string; message: string }[]
}

export interface ShoppingItem {
  id: string
  name: string
  quantity: string
  category: string
  category_label: string
  checked: boolean
  auto: boolean
  sources: string[]
  note: string | null
  added_by: string | null
}

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method,
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    let msg = `Fehler ${res.status}`
    try {
      const j = await res.json()
      if (typeof j.detail === 'string') msg = j.detail
    } catch { /* ignore */ }
    throw new Error(msg)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export const api = {
  info: () => req<AppInfo>('GET', 'api/info'),
  settings: () => req<Settings>('GET', 'api/settings'),
  saveSettings: (s: Partial<Settings>) => req<Settings>('PUT', 'api/settings', s),

  recipes: (q?: string) => req<Recipe[]>('GET', `api/recipes${q ? `?q=${encodeURIComponent(q)}` : ''}`),
  recipe: (id: string) => req<Recipe>('GET', `api/recipes/${id}`),
  createRecipe: (r: RecipeInput) => req<Recipe>('POST', 'api/recipes', r),
  updateRecipe: (id: string, r: RecipeInput) => req<Recipe>('PATCH', `api/recipes/${id}`, r),
  deleteRecipe: (id: string) => req<void>('DELETE', `api/recipes/${id}`),
  importRecipe: (url: string) => req<Recipe>('POST', 'api/recipes/import', { url }),
  rate: (id: string, stars: number) => req<Recipe>('POST', `api/recipes/${id}/ratings`, { stars }),

  plan: (start?: string, days?: number) => {
    const p = new URLSearchParams()
    if (start) p.set('start', start)
    if (days) p.set('days', String(days))
    return req<Plan>('GET', `api/plan?${p}`)
  },
  generate: (start: string, days: number, replace = false) => req<Plan>('POST', 'api/plan/generate', { start, days, replace }),
  addEntry: (e: { day: string; slot: string; recipe_id?: string; title?: string; servings?: number }) =>
    req<PlanEntry>('POST', 'api/plan/entries', e),
  updateEntry: (id: string, e: Partial<PlanEntry>) => req<PlanEntry>('PATCH', `api/plan/entries/${id}`, e),
  deleteEntry: (id: string) => req<void>('DELETE', `api/plan/entries/${id}`),
  swapEntry: (id: string) => req<PlanEntry>('POST', `api/plan/entries/${id}/swap`),

  shopping: () => req<ShoppingItem[]>('GET', 'api/shopping'),
  addShopping: (text: string) => req<ShoppingItem[]>('POST', 'api/shopping', { text }),
  updateShopping: (id: string, p: Partial<ShoppingItem>) => req<ShoppingItem>('PATCH', `api/shopping/${id}`, p),
  deleteShopping: (id: string) => req<void>('DELETE', `api/shopping/${id}`),
  clearChecked: () => req<ShoppingItem[]>('POST', 'api/shopping/clear-checked'),
  shoppingFromPlan: (start: string, days: number) => req<ShoppingItem[]>('POST', 'api/shopping/from-plan', { start, days }),
}
