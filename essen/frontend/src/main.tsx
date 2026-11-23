import { BookOpen, CalendarDays, Settings as SettingsIcon, ShoppingCart } from 'lucide-react'
import { StrictMode, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { HashRouter, NavLink, Route, Routes } from 'react-router-dom'
import { api, type AppInfo } from './api'
import './index.css'
import { InfoContext } from './info'
import PlanPage from './pages/PlanPage'
import RecipeDetail from './pages/RecipeDetail'
import RecipeEdit from './pages/RecipeEdit'
import RecipesPage from './pages/RecipesPage'
import SettingsPage from './pages/SettingsPage'
import ShoppingPage from './pages/ShoppingPage'
import { cls } from './util'

const NAV = [
  { to: '/', label: 'Plan', icon: CalendarDays, end: true },
  { to: '/rezepte', label: 'Rezepte', icon: BookOpen, end: false },
  { to: '/einkauf', label: 'Einkauf', icon: ShoppingCart, end: false },
  { to: '/einstellungen', label: 'Einstellungen', icon: SettingsIcon, end: false },
]

function Nav() {
  return (
    <>
      {/* Oben (Desktop) */}
      <header className="sticky top-0 z-30 hidden border-b border-slate-200/70 bg-white/80 backdrop-blur sm:block dark:border-slate-800 dark:bg-slate-950/80">
        <div className="mx-auto flex max-w-5xl items-center gap-2 px-6 py-3">
          <span className="mr-4 text-lg font-bold text-brand-700 dark:text-brand-300">Essen</span>
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end}
              className={({ isActive }) => cls('btn', isActive ? 'bg-brand-50 text-brand-700 dark:bg-brand-900/40 dark:text-brand-200' : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800')}>
              <Icon size={16} /> {label}
            </NavLink>
          ))}
        </div>
      </header>
      {/* Unten (Handy) */}
      <nav className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-4 border-t border-slate-200 bg-white/95 pb-[env(safe-area-inset-bottom)] backdrop-blur sm:hidden dark:border-slate-800 dark:bg-slate-950/95">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end}
            className={({ isActive }) => cls('flex flex-col items-center gap-0.5 py-2 text-[11px] font-medium', isActive ? 'text-brand-700 dark:text-brand-300' : 'text-slate-500')}>
            <Icon size={20} /> {label}
          </NavLink>
        ))}
      </nav>
    </>
  )
}

// HashRouter: funktioniert hinter HA Ingress ohne Kenntnis des Basis-Pfads
function App() {
  const [info, setInfo] = useState<AppInfo | null>(null)
  const reload = () => { api.info().then(setInfo).catch(() => {}) }
  useEffect(reload, [])
  return (
    <InfoContext.Provider value={{ info, reload }}>
      <HashRouter>
        <Nav />
        <main className="mx-auto max-w-5xl px-4 pb-28 pt-4 sm:px-6 sm:pb-12 sm:pt-6">
          <Routes>
            <Route path="/" element={<PlanPage />} />
            <Route path="/rezepte" element={<RecipesPage />} />
            <Route path="/rezepte/neu" element={<RecipeEdit />} />
            <Route path="/rezepte/:id" element={<RecipeDetail />} />
            <Route path="/rezepte/:id/bearbeiten" element={<RecipeEdit />} />
            <Route path="/einkauf" element={<ShoppingPage />} />
            <Route path="/einstellungen" element={<SettingsPage />} />
            <Route path="*" element={<PlanPage />} />
          </Routes>
        </main>
      </HashRouter>
    </InfoContext.Provider>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
