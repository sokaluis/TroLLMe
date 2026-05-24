import { useEffect, useState } from 'react'
import { fetchQuestions, fetchModels, fetchWorldviews } from '../api'
import type { ApiError, ModelInfo, Question, Worldview } from '../types'

interface BootstrapData {
  questions: Question[]
  setQuestions: React.Dispatch<React.SetStateAction<Question[]>>
  models: ModelInfo[]
  worldviews: Worldview[]
  loading: boolean
  error: ApiError | null
}

export function useBootstrapData(): BootstrapData {
  const [questions, setQuestions] = useState<Question[]>([])
  const [models, setModels] = useState<ModelInfo[]>([])
  const [worldviews, setWorldviews] = useState<Worldview[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<ApiError | null>(null)

  useEffect(() => {
    let cancelled = false
    Promise.all([fetchQuestions(), fetchModels(), fetchWorldviews()])
      .then(([qs, ms, ws]) => {
        if (cancelled) return
        setQuestions(qs)
        setModels(ms)
        setWorldviews(ws)
        setLoading(false)
      })
      .catch((err: ApiError) => {
        if (cancelled) return
        setError(err)
        setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  return { questions, setQuestions, models, worldviews, loading, error }
}
