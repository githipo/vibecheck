import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { getSession, generateQuiz, deleteSession, generateInsights, getInsights, SessionDetail as SessionDetailType } from '../api/sessions'

const SOURCE_LABELS: Record<string, string> = {
  claude_code: 'Claude Code',
  chatgpt: 'ChatGPT',
  cursor: 'Cursor',
  generic: 'Generic',
}

const STATUS_STYLES: Record<string, string> = {
  pending_quiz: 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30',
  quiz_active: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
  completed: 'bg-green-500/20 text-green-400 border border-green-500/30',
}

const STATUS_LABELS: Record<string, string> = {
  pending_quiz: 'Pending Quiz',
  quiz_active: 'Quiz Active',
  completed: 'Completed',
}

const formatDate = (iso: string): string => {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const SessionDetail = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const sessionId = Number(id)

  const [session, setSession] = useState<SessionDetailType | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [generatingQuiz, setGeneratingQuiz] = useState(false)
  const [quizError, setQuizError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [insightsExist, setInsightsExist] = useState(false)
  const [extractingInsights, setExtractingInsights] = useState(false)
  const [insightsError, setInsightsError] = useState<string | null>(null)

  useEffect(() => {
    if (isNaN(sessionId)) {
      setError('Invalid session ID')
      setLoading(false)
      return
    }

    const loadData = async () => {
      try {
        const sessionData = await getSession(sessionId)
        setSession(sessionData)
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to load session')
        setLoading(false)
        return
      }

      try {
        await getInsights(sessionId)
        setInsightsExist(true)
      } catch {
        setInsightsExist(false)
      }

      setLoading(false)
    }

    loadData()
  }, [sessionId])

  const handleGenerateQuiz = async () => {
    setQuizError(null)
    setGeneratingQuiz(true)
    try {
      await generateQuiz(sessionId)
      navigate(`/sessions/${sessionId}/quiz`)
    } catch (err: unknown) {
      setQuizError(err instanceof Error ? err.message : 'Failed to generate quiz')
      setGeneratingQuiz(false)
    }
  }

  const handleExtractInsights = async () => {
    setInsightsError(null)
    setExtractingInsights(true)
    try {
      await generateInsights(sessionId)
      navigate(`/sessions/${sessionId}/insights`)
    } catch (err: unknown) {
      setInsightsError(err instanceof Error ? err.message : 'Failed to extract insights')
      setExtractingInsights(false)
    }
  }

  const handleDelete = async () => {
    if (!confirmDelete) {
      setConfirmDelete(true)
      return
    }
    setDeleting(true)
    try {
      await deleteSession(sessionId)
      navigate('/')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to delete session')
      setDeleting(false)
      setConfirmDelete(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        <span className="ml-3 text-gray-400">Loading session...</span>
      </div>
    )
  }

  if (error || !session) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-10">
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-red-400 text-sm">
          {error ?? 'Session not found'}
        </div>
        <Link to="/" className="inline-block mt-4 text-gray-400 hover:text-gray-200 text-sm">
          ← Back to sessions
        </Link>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      <div className="mb-6">
        <Link to="/" className="text-gray-500 hover:text-gray-300 text-sm transition-colors">
          ← Back to sessions
        </Link>
      </div>

      <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 mb-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-gray-100">{session.title}</h1>
            <p className="text-gray-500 text-sm mt-1">{formatDate(session.created_at)}</p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <span className="bg-gray-800 border border-gray-600 text-gray-300 text-xs px-2 py-1 rounded-md font-mono">
              {SOURCE_LABELS[session.source_type] ?? session.source_type}
            </span>
            <span
              className={`text-xs px-2 py-1 rounded-md font-medium ${STATUS_STYLES[session.status] ?? 'bg-gray-700 text-gray-300'}`}
            >
              {STATUS_LABELS[session.status] ?? session.status}
            </span>
          </div>
        </div>

        <div className="mt-6 flex items-center gap-3">
          {session.status === 'pending_quiz' && (
            <button
              onClick={handleGenerateQuiz}
              disabled={generatingQuiz}
              className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 disabled:cursor-not-allowed text-white font-medium px-4 py-2 rounded-lg transition-colors text-sm"
            >
              {generatingQuiz ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Generating quiz...
                </>
              ) : (
                'Generate Quiz'
              )}
            </button>
          )}

          {session.status === 'quiz_active' && (
            <Link
              to={`/sessions/${sessionId}/quiz`}
              className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-medium px-4 py-2 rounded-lg transition-colors text-sm"
            >
              Take Quiz
            </Link>
          )}

          {session.status === 'completed' && (
            <>
              <Link
                to={`/sessions/${sessionId}/results`}
                className="inline-flex items-center gap-2 bg-green-700 hover:bg-green-600 text-white font-medium px-4 py-2 rounded-lg transition-colors text-sm"
              >
                View Results
              </Link>
              <Link
                to={`/sessions/${sessionId}/quiz`}
                className="inline-flex items-center gap-2 bg-gray-700 hover:bg-gray-600 text-gray-200 font-medium px-4 py-2 rounded-lg transition-colors text-sm"
              >
                Retake Quiz
              </Link>
            </>
          )}

          {insightsExist ? (
            <Link
              to={`/sessions/${sessionId}/insights`}
              className="inline-flex items-center gap-2 border border-indigo-500 text-indigo-400 hover:bg-indigo-500/10 font-medium px-4 py-2 rounded-lg transition-colors text-sm"
            >
              View Insights
            </Link>
          ) : (
            <button
              onClick={handleExtractInsights}
              disabled={extractingInsights}
              className="inline-flex items-center gap-2 border border-indigo-500 text-indigo-400 hover:bg-indigo-500/10 disabled:opacity-60 disabled:cursor-not-allowed font-medium px-4 py-2 rounded-lg transition-colors text-sm"
            >
              {extractingInsights ? (
                <>
                  <div className="w-4 h-4 border-2 border-indigo-400/30 border-t-indigo-400 rounded-full animate-spin" />
                  Extracting insights...
                </>
              ) : (
                'Extract Insights'
              )}
            </button>
          )}

          <button
            onClick={handleDelete}
            disabled={deleting}
            className={`inline-flex items-center gap-2 font-medium px-4 py-2 rounded-lg transition-colors text-sm ml-auto ${
              confirmDelete
                ? 'bg-red-600 hover:bg-red-500 text-white'
                : 'bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-red-400 border border-gray-700'
            }`}
          >
            {deleting ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Deleting...
              </>
            ) : confirmDelete ? (
              'Confirm Delete'
            ) : (
              'Delete Session'
            )}
          </button>
          {confirmDelete && !deleting && (
            <button
              onClick={() => setConfirmDelete(false)}
              className="text-sm text-gray-500 hover:text-gray-300 transition-colors"
            >
              Cancel
            </button>
          )}
        </div>

        {quizError && (
          <div className="mt-4 bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-red-400 text-sm">
            {quizError}
          </div>
        )}

        {insightsError && (
          <div className="mt-4 bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-red-400 text-sm">
            {insightsError}
          </div>
        )}

        {extractingInsights && (
          <div className="mt-4 bg-indigo-500/10 border border-indigo-500/20 rounded-lg px-4 py-3 text-indigo-300 text-sm">
            Claude is extracting decisions, patterns, and gotchas from your transcript. This usually takes 5–10 seconds...
          </div>
        )}

        {generatingQuiz && (
          <div className="mt-4 bg-indigo-500/10 border border-indigo-500/20 rounded-lg px-4 py-3 text-indigo-300 text-sm">
            Claude is analyzing your transcript and generating quiz questions. This usually takes 5–15 seconds...
          </div>
        )}
      </div>

      <div className="bg-gray-900 border border-gray-700 rounded-xl p-6">
        <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-4">Transcript</h2>
        <pre className="text-gray-300 text-xs font-mono leading-relaxed whitespace-pre-wrap overflow-auto max-h-[500px] scrollbar-thin scrollbar-thumb-gray-700">
          {session.transcript}
        </pre>
      </div>
    </div>
  )
}

export default SessionDetail
