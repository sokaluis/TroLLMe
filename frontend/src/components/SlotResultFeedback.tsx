import type { ApiError, Slot, SlotRunState } from '../types'

interface Props {
  slots: Slot[]
  slotStates: Record<string, SlotRunState>
  askError: ApiError | null
}

export default function SlotResultFeedback({ slots, slotStates, askError }: Props) {
  if (slots.length === 0) return null

  const slotErrors = slots.filter((s) => slotStates[s.slot_id] === 'error')

  if (slotErrors.length === 0 && !askError) return null

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-4 space-y-2">
      <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide">Slot Status</h3>
      {askError && (
        <div className="flex items-start gap-2 p-2.5 rounded-lg bg-red-50 border border-red-100">
          <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-red-400 mt-0.5 shrink-0" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          <p className="text-sm text-red-600">{askError.message}</p>
        </div>
      )}
      {slotErrors.map((s) => (
        <div key={s.slot_id} className="flex items-start gap-2 p-2.5 rounded-lg bg-amber-50 border border-amber-100">
          <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          <p className="text-sm text-amber-700">
            <span className="font-medium">Slot {slots.findIndex((sl) => sl.slot_id === s.slot_id) + 1}</span>
            {' '}returned an error. Check model or worldview configuration.
          </p>
        </div>
      ))}
    </div>
  )
}
