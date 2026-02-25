import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  getSession,
  getInsights,
  applyInsights,
  SessionDetail,
  Insight,
} from '../api/sessions'

const EmptyState = ({ label }: { label: string }) => (
  <p className="text-gray-600 text-sm italic">{label}</p>
)

const Insights = () => {
  const { id } = useParams<{ id: string }>()
  const sessionId = Number(id)

  const [session, setSession] = useState<SessionDetail | null>(null)
  const [insight, setInsight] = useState<Insight | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [filePath, setFilePath] = useState('')
  const [applying, setApplying] = useState(false)
  const [applySuccess, setApplySuccess] = useState<{ charsAdded: number; filePath: string } | null>(null)
  const [applyError, setApplyError] = useState<string | null>(null)

  useEffect(() => {
    if (isNaN(sessionId)) {
      setError('Invalid session ID')
      setLoading(false)
      return
    }

    Promise.all([getSession(sessionId), getInsights(sessionId)])
      .then(([sessionData, insightData]) => {
        setSession(sessionData)
        setInsight(insightData)
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : 'Failed to load insights'))
      .finally(() => setLoading(false))
  }, [sessionId])

  const handleRetry = () => {
    setError(null)
    setLoading(true)
    Promise.all([getSession(sessionId), getInsights(sessionId)])
      .then(([sessionData, insightData]) => {
        setSession(sessionData)
        setInsight(insightData)
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : 'Failed to load insights'))
      .finally(() => setLoading(false))
  }

  const handleApply = async () => {
    setApplyError(null)
    setApplySuccess(null)
    setApplying(true)
    try {
      const result = await applyInsights(sessionId, filePath)
      setApplySuccess({ charsAdded: result.chars_added, filePath: result.file_path })
    } catch (err: unknown) {
      setApplyError(err instanceof Error ? err.message : 'Failed to apply insights')
    } finally {
      setApplying(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        <span className="ml-3 text-gray-400">Analyzing session...</span>
      </div>
    )
  }

  if (error || !insight) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-10">
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-red-400 text-sm">
          {error ?? 'Insights not found'}
        </div>
        <div className="flex items-center gap-4 mt-4">
          <button
            onClick={handleRetry}
            className="text-sm text-indigo-400 hover:text-indigo-300 transition-colors"
          >
            Retry
          </button>
          <Link to={`/sessions/${sessionId}`} className="text-gray-400 hover:text-gray-200 text-sm">
            ← Back to session
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      <div className="mb-6">
        <Link
          to={`/sessions/${sessionId}`}
          className="text-gray-500 hover:text-gray-300 text-sm transition-colors"
        >
          ← Back to session
        </Link>
      </div>

      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-100">Session Intelligence</h1>
        {session && (
          <p className="text-gray-500 text-sm mt-1">{session.title}</p>
        )}
      </div>

      <div className="space-y-6">
        {/* Decisions Made */}
        <div className="bg-gray-900 border border-gray-700 rounded-xl overflow-hidden">
          <div className="border-l-4 border-indigo-500 px-6 py-4">
            <h2 className="text-sm font-semibold text-indigo-400 uppercase tracking-wider">
              Decisions Made
            </h2>
          </div>
          <div className="px-6 pb-5 space-y-4">
            {insight.decisions.length === 0 ? (
              <EmptyState label="None identified in this session" />
            ) : (
              insight.decisions.map((d, i) => (
                <div key={i} className="border-t border-gray-800 pt-4 first:border-t-0 first:pt-0">
                  <p className="text-gray-100 font-medium text-sm">{d.decision}</p>
                  <p className="text-gray-400 text-sm mt-1 leading-relaxed">{d.rationale}</p>
                  {d.alternatives_rejected.length > 0 && (
                    <p className="text-gray-600 text-xs mt-1.5">
                      Considered: {d.alternatives_rejected.join(', ')}
                    </p>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Patterns Established */}
        <div className="bg-gray-900 border border-gray-700 rounded-xl overflow-hidden">
          <div className="border-l-4 border-violet-500 px-6 py-4">
            <h2 className="text-sm font-semibold text-violet-400 uppercase tracking-wider">
              Patterns Established
            </h2>
          </div>
          <div className="px-6 pb-5 space-y-4">
            {insight.patterns.length === 0 ? (
              <EmptyState label="None identified in this session" />
            ) : (
              insight.patterns.map((p, i) => (
                <div key={i} className="border-t border-gray-800 pt-4 first:border-t-0 first:pt-0">
                  <p className="text-gray-100 font-medium text-sm">{p.pattern}</p>
                  <p className="text-gray-400 text-sm mt-1 leading-relaxed">{p.description}</p>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Gotchas & Constraints */}
        <div className="bg-gray-900 border border-gray-700 rounded-xl overflow-hidden">
          <div className="border-l-4 border-amber-500 px-6 py-4">
            <h2 className="text-sm font-semibold text-amber-400 uppercase tracking-wider">
              Gotchas &amp; Constraints
            </h2>
          </div>
          <div className="px-6 pb-5 space-y-4">
            {insight.gotchas.length === 0 ? (
              <EmptyState label="None identified in this session" />
            ) : (
              insight.gotchas.map((g, i) => (
                <div key={i} className="border-t border-gray-800 pt-4 first:border-t-0 first:pt-0">
                  <div className="flex items-start gap-2">
                    <span className="text-amber-500 text-xs mt-0.5 flex-shrink-0">&#9888;</span>
                    <p className="text-gray-100 font-medium text-sm">{g.issue}</p>
                  </div>
                  <p className="text-gray-400 text-sm mt-1 leading-relaxed pl-4">{g.context}</p>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Proposed CLAUDE.md Additions */}
        <div className="bg-gray-900 border border-gray-700 rounded-xl overflow-hidden">
          <div className="border-l-4 border-emerald-500 px-6 py-4">
            <h2 className="text-sm font-semibold text-emerald-400 uppercase tracking-wider">
              Proposed CLAUDE.md Additions
            </h2>
          </div>
          <div className="px-6 pb-5 space-y-4">
            {insight.proposed_rules.length === 0 ? (
              <EmptyState label="None identified in this session" />
            ) : (
              insight.proposed_rules.map((r, i) => (
                <div
                  key={i}
                  className="border-t border-gray-800 pt-4 first:border-t-0 first:pt-0"
                >
                  <div className="flex items-start gap-3">
                    <span className="bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs px-2 py-0.5 rounded-md font-mono flex-shrink-0">
                      {r.section}
                    </span>
                    <div>
                      <p className="text-gray-100 font-medium text-sm">{r.rule}</p>
                      <p className="text-gray-400 text-sm mt-1 leading-relaxed">{r.rationale}</p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {insight.proposed_rules.length > 0 && (
            <div className="mx-6 mb-6 bg-gray-800/60 border border-gray-700 rounded-lg p-5">
              <h3 className="text-sm font-semibold text-gray-200 mb-1">Apply to CLAUDE.md</h3>
              <p className="text-gray-500 text-xs mb-4">
                Paste the absolute path to the CLAUDE.md file you want to update
              </p>
              <label className="block text-xs font-medium text-gray-400 mb-1.5">
                CLAUDE.md path
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={filePath}
                  onChange={(e) => setFilePath(e.target.value)}
                  placeholder="/Users/you/project/CLAUDE.md"
                  className="flex-1 bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-600 focus:outline-none focus:border-emerald-500 font-mono"
                />
                <button
                  onClick={handleApply}
                  disabled={applying || filePath.trim() === ''}
                  className="inline-flex items-center gap-2 bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium px-4 py-2 rounded-lg transition-colors text-sm flex-shrink-0"
                >
                  {applying ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Applying...
                    </>
                  ) : (
                    'Apply'
                  )}
                </button>
              </div>

              {applySuccess && (
                <div className="mt-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg px-3 py-2.5 text-emerald-400 text-sm">
                  Added {applySuccess.charsAdded} characters to {applySuccess.filePath}
                </div>
              )}
              {applyError && (
                <div className="mt-3 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2.5 text-red-400 text-sm">
                  {applyError}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Insights
