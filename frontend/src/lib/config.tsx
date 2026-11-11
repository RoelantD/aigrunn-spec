import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { api } from '../api/client'
import type { PublicConfig } from '../api/types'

const Ctx = createContext<PublicConfig | null>(null)

export function ConfigProvider({ children }: { children: ReactNode }) {
  const [cfg, setCfg] = useState<PublicConfig | null>(null)
  useEffect(() => {
    api.config().then(setCfg).catch(() => {})
  }, [])
  return <Ctx.Provider value={cfg}>{children}</Ctx.Provider>
}

export function useConfig() {
  return useContext(Ctx)
}

export function useModelNames() {
  const c = useConfig()
  return {
    workhorse: c?.workhorse.display_name ?? 'GPT-6.1 Sol',
    escalation: c?.escalation.display_name ?? 'Claude Opus 5.5',
  }
}
