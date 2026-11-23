import { createContext, useContext } from 'react'
import type { AppInfo } from './api'

export const InfoContext = createContext<{ info: AppInfo | null; reload: () => void }>({ info: null, reload: () => {} })
export const useInfo = () => useContext(InfoContext)
