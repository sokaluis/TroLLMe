import { useRef, useState } from 'react'
import { useBootstrapData } from './hooks/useBootstrapData'
import { useSlotsPersistence } from './hooks/useSlotsPersistence'
import { useAskFlow } from './hooks/useAskFlow'
import { useQuestionMutations } from './hooks/useQuestionMutations'
import ConfirmationUI from './components/ConfirmationUI'
import EmptyState from './components/EmptyState'
import ExportButton from './components/ExportButton'
import QuestionCard from './components/QuestionCard'
import QuestionFormModal from './components/QuestionFormModal'
import ResultsTable from './components/ResultsTable'
import SlotConfigurator from './components/SlotConfigurator'
import SlotResultFeedback from './components/SlotResultFeedback'
import UploadButton from './components/UploadButton'
import type { ModelResponse, Question, QuestionCreate, Slot } from './types'

type ModalState =
  | { mode: 'create' }
  | { mode: 'edit'; question: Question }
  | null

export default function App() {
  const {
    questions,
    setQuestions,
    models,
    worldviews,
    loading: bootLoading,
    error: bootError,
  } = useBootstrapData()

  const { slots, setSlots } = useSlotsPersistence(models, worldviews)
  const { ask, slotStates, loading: askLoading, error: askError } = useAskFlow(slots)
  const { create, update, remove } = useQuestionMutations()

  const [index, setIndex] = useState(0)
  const [responsesMap, setResponsesMap] = useState<Record<number, ModelResponse[]>>({})
  const [modal, setModal] = useState<ModalState>(null)
  const [deleteConfirm, setDeleteConfirm] = useState(false)

  const prevSlotsRef = useRef<Slot[]>([])

  function handleSlotsChange(newSlots: Slot[]) {
    const prev = prevSlotsRef.current
    const changedSlotIds = new Set(
      newSlots
        .filter((s) => {
          const old = prev.find((p) => p.slot_id === s.slot_id)
          return old && (old.model_id !== s.model_id || old.worldview_id !== s.worldview_id)
        })
        .map((s) => s.slot_id),
    )
    const removedSlotIds = new Set(
      prev.filter((p) => !newSlots.find((s) => s.slot_id === p.slot_id)).map((p) => p.slot_id),
    )

    if (changedSlotIds.size > 0 || removedSlotIds.size > 0) {
      setResponsesMap((prevMap) => {
        const next: Record<number, ModelResponse[]> = {}
        for (const [qid, resps] of Object.entries(prevMap)) {
          const filtered = resps.filter(
            (r) => !changedSlotIds.has(r.slot_id) && !removedSlotIds.has(r.slot_id),
          )
          next[Number(qid)] = filtered
        }
        return next
      })
    }

    prevSlotsRef.current = newSlots
    setSlots(newSlots)
  }

  const question = questions[index] ?? null

  async function handleAsk() {
    if (!question || slots.length === 0) return
    const responses = await ask(question.id)
    if (responses.length > 0) {
      setResponsesMap((prev) => ({ ...prev, [question.id]: responses }))
    }
  }

  async function handleUploaded(newQuestions: Question[]) {
    setQuestions(newQuestions)
    setIndex(0)
    setResponsesMap({})
  }

  async function handleSaveQuestion(data: QuestionCreate) {
    if (modal?.mode === 'edit') {
      const updated = await update(modal.question.id, data)
      if (updated) {
        setQuestions((prev) => prev.map((q) => (q.id === updated.id ? updated : q)))
      }
    } else {
      const created = await create(data)
      if (created) {
        setQuestions((prev) => {
          const next = [...prev, created]
          setIndex(next.length - 1)
          return next
        })
      }
    }
    setModal(null)
  }

  async function handleDeleteQuestion() {
    if (!question) return
    const ok = await remove(question.id)
    if (ok) {
      setResponsesMap((prev) => {
        const next = { ...prev }
        delete next[question.id]
        return next
      })
      setQuestions((prev) => {
        const next = prev.filter((q) => q.id !== question.id)
        setIndex((i) => Math.min(i, Math.max(0, next.length - 1)))
        return next
      })
    }
  }

  const currentResponses = question ? (responsesMap[question.id] ?? []) : []

  // --- Render paths ---

  if (bootError) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white rounded-2xl shadow-sm border border-red-200 p-8 max-w-md text-center">
          <p className="text-red-600 font-semibold mb-2">Failed to load</p>
          <p className="text-gray-500 text-sm">{bootError.message}</p>
        </div>
      </div>
    )
  }

  if (bootLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-pulse space-y-4 text-center">
          <div className="mx-auto w-16 h-16 rounded-2xl bg-gray-200" />
          <p className="text-gray-400 text-sm">Loading…</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {modal && (
        <QuestionFormModal
          initial={modal.mode === 'edit' ? modal.question : undefined}
          onSave={handleSaveQuestion}
          onCancel={() => setModal(null)}
        />
      )}

      {deleteConfirm && question && (
        <ConfirmationUI
          message={`Delete "${question.title}"? This cannot be undone.`}
          confirmLabel="Delete"
          variant="danger"
          onConfirm={() => {
            setDeleteConfirm(false)
            handleDeleteQuestion()
          }}
          onCancel={() => setDeleteConfirm(false)}
        />
      )}

      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <span className="text-2xl" aria-hidden>🚃</span>
            <span className="font-bold text-gray-900 text-lg tracking-tight">Trolley to LLM</span>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setModal({ mode: 'create' })}
              className="px-3 py-1.5 rounded-lg text-sm font-medium bg-indigo-600 text-white hover:bg-indigo-700 transition-colors"
            >
              + Add Question
            </button>
            <UploadButton onUploaded={handleUploaded} />
            <ExportButton />
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        {questions.length === 0 ? (
          <EmptyState
            onAdd={() => setModal({ mode: 'create' })}
            onUpload={() => document.querySelector<HTMLInputElement>('input[type="file"]')?.click()}
          />
        ) : question ? (
          <>
            <SlotConfigurator
              slots={slots}
              models={models}
              worldviews={worldviews}
              onChange={handleSlotsChange}
            />

            <QuestionCard
              question={question}
              current={index + 1}
              total={questions.length}
              onPrev={() => setIndex((i) => Math.max(0, i - 1))}
              onNext={() => setIndex((i) => Math.min(questions.length - 1, i + 1))}
              onAsk={handleAsk}
              onEdit={() => setModal({ mode: 'edit', question })}
              onDelete={() => setDeleteConfirm(true)}
              loading={askLoading}
            />

            <SlotResultFeedback
              slots={slots}
              slotStates={slotStates}
              askError={askError}
            />

            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
              <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-4">
                Model Responses
              </h3>
              <ResultsTable
                slots={slots}
                responses={currentResponses}
                loading={askLoading}
              />
            </div>
          </>
        ) : null}
      </main>
    </div>
  )
}
