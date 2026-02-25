import { FormEvent, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { createSession } from '../api/sessions'

const SOURCE_OPTIONS = [
  { value: 'claude_code', label: 'Claude Code' },
  { value: 'chatgpt', label: 'ChatGPT' },
  { value: 'cursor', label: 'Cursor' },
  { value: 'generic', label: 'Generic / Other' },
]

const NewSession = () => {
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [sourceType, setSourceType] = useState('claude_code')
  const [transcript, setTranscript] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!title.trim() || !transcript.trim()) {
      setError('All fields are required.')
      return
    }

    setSubmitting(true)
    try {
      const session = await createSession({
        title: title.trim(),
        transcript: transcript.trim(),
        source_type: sourceType,
      })
      navigate(`/sessions/${session.id}`)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create session')
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-10">
      <div className="mb-8">
        <Link to="/" className="text-gray-500 hover:text-gray-300 text-sm transition-colors">
          ← Back to sessions
        </Link>
        <h1 className="text-2xl font-bold text-gray-100 mt-4">New Session</h1>
        <p className="text-gray-400 text-sm mt-1">
          Paste your AI session transcript to generate a comprehension quiz
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-red-400 text-sm">
            {error}
          </div>
        )}

        <div>
          <label htmlFor="title" className="block text-sm font-medium text-gray-300 mb-1.5">
            Session Title
          </label>
          <input
            id="title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Building authentication with FastAPI"
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2.5 text-gray-100 placeholder-gray-500 text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
            disabled={submitting}
          />
        </div>

        <div>
          <label htmlFor="source_type" className="block text-sm font-medium text-gray-300 mb-1.5">
            Source Type
          </label>
          <select
            id="source_type"
            value={sourceType}
            onChange={(e) => setSourceType(e.target.value)}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2.5 text-gray-100 text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors appearance-none cursor-pointer"
            disabled={submitting}
          >
            {SOURCE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="transcript" className="block text-sm font-medium text-gray-300 mb-1.5">
            Transcript
          </label>
          <textarea
            id="transcript"
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            placeholder="Paste your AI session transcript here..."
            rows={16}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2.5 text-gray-100 placeholder-gray-500 text-sm font-mono focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors resize-y"
            disabled={submitting}
          />
          <p className="text-gray-600 text-xs mt-1">
            {transcript.length > 0 ? `${transcript.length.toLocaleString()} characters` : 'Minimum recommended: 500 characters for good quiz quality'}
          </p>
        </div>

        <div className="flex items-center justify-end gap-3 pt-2">
          <Link
            to="/"
            className="text-sm text-gray-400 hover:text-gray-200 transition-colors px-4 py-2"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={submitting}
            className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 disabled:cursor-not-allowed text-white font-medium px-5 py-2.5 rounded-lg transition-colors text-sm"
          >
            {submitting ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Creating...
              </>
            ) : (
              'Create Session'
            )}
          </button>
        </div>
      </form>
    </div>
  )
}

export default NewSession
