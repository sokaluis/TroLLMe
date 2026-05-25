import { useMemo, useState } from 'react'
import type { ModelInfo, Slot, Worldview } from '../types'

const STORAGE_KEY = 'trollme-slots'

function makeDefaultSlots(models: ModelInfo[], worldviews: Worldview[]): Slot[] {
  const defaultWorldview = worldviews[0]?.id ?? ''
  return models.map((m, i) => ({
    slot_id: `slot-init-${i}`,
    model_id: m.model_id,
    worldview_id: defaultWorldview,
  }))
}

function loadFromStorage(): Slot[] | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (Array.isArray(parsed) && parsed.length > 0) return parsed as Slot[]
  } catch {
    /* corrupted data — fall through to defaults */
  }
  return null
}

function saveToStorage(slots: Slot[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(slots))
  } catch {
    /* quota exceeded or storage unavailable — silently degrade */
  }
}

export function useSlotsPersistence(models: ModelInfo[], worldviews: Worldview[]) {
  const modelsReady = models.length > 0
  const defaultSlots = useMemo(
    () => (modelsReady ? makeDefaultSlots(models, worldviews) : []),
    [modelsReady, models, worldviews],
  )

  const [storedSlots, setStoredSlots] = useState<Slot[] | null>(() => loadFromStorage())
  const slots = storedSlots ?? defaultSlots

  function setSlots(nextOrFn: Slot[] | ((prev: Slot[]) => Slot[])) {
    setStoredSlots((prev) => {
      const current = prev ?? defaultSlots
      const next = typeof nextOrFn === 'function' ? nextOrFn(current) : nextOrFn
      saveToStorage(next)
      return next
    })
  }

  return { slots, setSlots }
}
