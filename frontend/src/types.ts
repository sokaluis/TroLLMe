export interface Question {
  id: number
  title: string
  prompt: string
  options: string[]
}

export interface QuestionCreate {
  title: string
  prompt: string
  options: string[]
}

export interface ModelInfo {
  model_id: string
  display_name: string
}

export interface Worldview {
  id: string
  label: string
  system_prompt: string
}

export interface Slot {
  slot_id: string
  model_id: string
  worldview_id: string
}

export interface ModelResponse {
  slot_id: string
  model_id: string
  display_name: string
  worldview_id: string
  worldview_label: string
  choice: string | null
  reasoning: string | null
  moral_framework: string | null
  error: string | null
}

export interface AskResponse {
  question_id: number
  responses: ModelResponse[]
}

export type SlotRunState = 'idle' | 'loading' | 'success' | 'error'

export interface ApiError {
  message: string
  status?: number
  detail?: unknown
}

export interface ImageOperationResult {
  question_id: number
  cached: boolean
  media_type: string
}
