import { useState } from 'react'
import { generateQuestionImage, getQuestionImageUrl } from '../api'
import type { ApiError } from '../types'

interface Props {
  questionId: number
  questionTitle: string
  onLightbox?: () => void
  onImageGenerated?: () => void
}

export default function ImageControls({ questionId, questionTitle, onLightbox, onImageGenerated }: Props) {
  const [bust, setBust] = useState(0)
  const [imgLoading, setImgLoading] = useState(true)
  const [imgError, setImgError] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [genError, setGenError] = useState<ApiError | null>(null)

  const imageUrl = getQuestionImageUrl(questionId, bust)

  function handleImageLoad() {
    setImgLoading(false)
    setImgError(false)
    setGenError(null)
  }

  function handleImageError() {
    setImgLoading(false)
    setImgError(true)
  }

  async function handleGenerate() {
    setGenerating(true)
    setGenError(null)
    try {
      await generateQuestionImage(questionId)
      setImgError(false)
      setImgLoading(true)
      setBust((v) => v + 1)
      onImageGenerated?.()
    } catch (err) {
      setGenError(err as ApiError)
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="relative group">
      {imgError ? (
        <div className="w-full h-48 bg-gray-100 flex flex-col items-center justify-center gap-3 rounded-t-2xl">
          <svg xmlns="http://www.w3.org/2000/svg" className="w-10 h-10 text-gray-300" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd" />
          </svg>
          <p className="text-sm text-gray-400">No illustration yet</p>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="px-4 py-1.5 rounded-lg text-sm font-medium bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {generating ? 'Generating…' : 'Generate Illustration'}
          </button>
          {genError && (
            <p className="text-xs text-red-500">{genError.message}</p>
          )}
        </div>
      ) : (
        <>
          {imgLoading && (
            <div className="w-full h-48 bg-gray-100 animate-pulse rounded-t-2xl" />
          )}
          <img
            key={imageUrl}
            src={imageUrl}
            alt={questionTitle}
            onLoad={handleImageLoad}
            onError={handleImageError}
            onClick={() => !imgLoading && onLightbox?.()}
            className={`w-full h-48 object-cover transition-opacity duration-300 cursor-zoom-in ${imgLoading ? 'opacity-0 absolute inset-0' : 'opacity-100'}`}
          />
          {!imgLoading && (
            <button
              onClick={handleGenerate}
              disabled={generating}
              className="absolute top-2 right-2 p-1.5 rounded-lg bg-black/40 text-white opacity-0 group-hover:opacity-100 hover:bg-black/60 disabled:opacity-40 transition-all"
              title="Regenerate illustration"
              aria-label="Regenerate illustration"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className={`w-4 h-4 ${generating ? 'animate-spin' : ''}`} viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
              </svg>
            </button>
          )}
        </>
      )}
    </div>
  )
}
