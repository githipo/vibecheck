import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listSessions, Session } from '../api/sessions'

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

const Home = () => {
  const [sessions, setSessions] = useState<Session[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listSessions()
      .then(setSessions)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : 'Failed to load sessions'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-100 tracking-tight">VibeCheck</h1>
          <p className="text-gray-400 mt-1 text-sm">Verify what you actually understand from your AI sessions</p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            to="/analytics"
            className="inline-flex items-center gap-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 text-gray-300 font-medium px-4 py-2 rounded-lg transition-colors text-sm"
          >
            Analytics
          </Link>
          <Link
            to="/codebase"
            className="inline-flex items-center gap-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 text-gray-300 font-medium px-4 py-2 rounded-lg transition-colors text-sm"
          >
            Codebase Map
          </Link>
          <Link
            to="/codebase/brief"
            className="inline-flex items-center gap-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 text-gray-300 font-medium px-4 py-2 rounded-lg transition-colors text-sm"
          >
            AI Brief
          </Link>
          <Link
            to="/repos"
            className="inline-flex items-center gap-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 text-gray-300 font-medium px-4 py-2 rounded-lg transition-colors text-sm"
          >
            Multi-Repo
          </Link>
          <Link
            to="/sessions/new"
            className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-4 py-2 rounded-lg transition-colors text-sm"
          >
            <span className="text-lg leading-none">+</span>
            New Session
          </Link>
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-20">
          <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          <span className="ml-3 text-gray-400">Loading sessions...</span>
        </div>
      )}

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-red-400 text-sm">
          {error}
        </div>
      )}

      {!loading && !error && sessions.length === 0 && (
        <div className="text-center py-20 border border-dashed border-gray-700 rounded-xl">
          <div className="text-4xl mb-4">🧠</div>
          <h2 className="text-gray-300 font-semibold text-lg mb-2">No sessions yet</h2>
          <p className="text-gray-500 text-sm mb-6">Paste an AI session transcript to get started</p>
          <Link
            to="/sessions/new"
            className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-4 py-2 rounded-lg transition-colors text-sm"
          >
            Create your first session
          </Link>
        </div>
      )}

      {!loading && !error && sessions.length > 0 && (
        <div className="space-y-3">
          {sessions.map((session) => (
            <Link
              key={session.id}
              to={`/sessions/${session.id}`}
              className="block bg-gray-900 border border-gray-700 rounded-xl px-5 py-4 hover:border-indigo-500/50 hover:bg-gray-800 transition-all group"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <h2 className="text-gray-100 font-medium text-base truncate group-hover:text-indigo-300 transition-colors">
                    {session.title}
                  </h2>
                  <p className="text-gray-500 text-xs mt-1">{formatDate(session.created_at)}</p>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className="bg-gray-800 border border-gray-600 text-gray-300 text-xs px-2 py-0.5 rounded-md font-mono">
                    {SOURCE_LABELS[session.source_type] ?? session.source_type}
                  </span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-md font-medium ${STATUS_STYLES[session.status] ?? 'bg-gray-700 text-gray-300'}`}
                  >
                    {STATUS_LABELS[session.status] ?? session.status}
                  </span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

export default Home
