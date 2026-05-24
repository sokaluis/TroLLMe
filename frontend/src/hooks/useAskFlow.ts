import { useCallback, useEffect, useRef, useState } from 'react'
import { askQuestion } from '../api'
import type { ApiError, ModelResponse, Slot, SlotRunState } from '../types'

interface AskFlow {
  ask: (questionId: number) => Promise<ModelResponse[]>
  slotStates: Record<string, SlotRunState>
  loading: boolean
  error: ApiError | null
}

export function useAskFlow(slots: Slot[]): AskFlow {
  const [slotStates, setSlotStates] = useState<Record<string, SlotRunState>>({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)
  const slotsRef = useRef(slots)
  useEffect(() => { slotsRef.current = slots })

  const ask = useCallback(async (questionId: number): Promise<ModelResponse[]> => {
    const currentSlots = slotsRef.current
    if (currentSlots.length === 0) return []

    const initial: Record<string, SlotRunState> = {}
    currentSlots.forEach((s) => { initial[s.slot_id] = 'loading' })
    setSlotStates(initial)
    setLoading(true)
    setError(null)

    try {
      const result = await askQuestion(questionId, currentSlots)
      const final: Record<string, SlotRunState> = {}
      currentSlots.forEach((s) => {
        const resp = result.responses.find((r) => r.slot_id === s.slot_id)
        final[s.slot_id] = resp && !resp.error ? 'success' : 'error'
      })
      setSlotStates(final)
      return result.responses
    } catch (err) {
      const apiError = err as ApiError
      const final: Record<string, SlotRunState> = {}
      currentSlots.forEach((s) => { final[s.slot_id] = 'error' })
      setSlotStates(final)
      setError(apiError)
      return []
    } finally {
      setLoading(false)
    }
  }, [])

  return { ask, slotStates, loading, error }
}
