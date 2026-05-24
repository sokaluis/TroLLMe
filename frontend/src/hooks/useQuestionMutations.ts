import { useCallback, useState } from 'react'
import {
  createQuestion,
  deleteQuestion,
  updateQuestion,
  uploadQuestions,
} from '../api'
import type { ApiError, Question, QuestionCreate } from '../types'

interface QuestionMutations {
  create: (data: QuestionCreate) => Promise<Question | null>
  update: (id: number, data: Partial<QuestionCreate>) => Promise<Question | null>
  remove: (id: number) => Promise<boolean>
  upload: (file: File) => Promise<Question[] | null>
  error: ApiError | null
  clearError: () => void
}

export function useQuestionMutations(): QuestionMutations {
  const [error, setError] = useState<ApiError | null>(null)

  const clearError = useCallback(() => setError(null), [])

  const create = useCallback(async (data: QuestionCreate): Promise<Question | null> => {
    setError(null)
    try {
      return await createQuestion(data)
    } catch (err) {
      setError(err as ApiError)
      return null
    }
  }, [])

  const update = useCallback(async (id: number, data: Partial<QuestionCreate>): Promise<Question | null> => {
    setError(null)
    try {
      return await updateQuestion(id, data)
    } catch (err) {
      setError(err as ApiError)
      return null
    }
  }, [])

  const remove = useCallback(async (id: number): Promise<boolean> => {
    setError(null)
    try {
      await deleteQuestion(id)
      return true
    } catch (err) {
      setError(err as ApiError)
      return false
    }
  }, [])

  const upload = useCallback(async (file: File): Promise<Question[] | null> => {
    setError(null)
    try {
      return await uploadQuestions(file)
    } catch (err) {
      setError(err as ApiError)
      return null
    }
  }, [])

  return { create, update, remove, upload, error, clearError }
}
