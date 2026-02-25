import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getAnalytics, getCatchup, Analytics, TopicScore, CatchupBrief } from '../api/sessions'

const scoreColor = (score: number): string => {
  if (score >= 75) return 'text-green-400'
  if (score >= 50) return 'text-yellow-400'
  return 'text-red-400'
}

const scoreBarColor = (score: number): string => {
  if (score >= 75) return 'bg-green-500'
  if (score >= 50) return 'bg-yellow-500'
  return 'bg-red-500'
}

const scoreBorderColor = (score: number): string => {
  if (score >= 75) return 'border-green-500'
  if (score >= 50) return 'border-yellow-500'
  return 'border-red-500'
}

interface StatCardProps {
  label: string
  value: string | number
  valueClass?: string
}

const StatCard = ({ label, value, valueClass = 'text-gray-100' }: StatCardProps) => (
  <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
    <p className="text-gray-400 text-xs uppercase tracking-widest mb-2">{label}</p>
    <p className={`text-4xl font-bold ${valueClass}`}>{value}</p>
  </div>
)

interface ScoreBarProps {
  score: number
}

const ScoreBar = ({ score }: ScoreBarProps) => (
  <div className="flex items-center gap-3 flex-1">
    <div className="flex-1 bg-gray-700 rounded-full h-2 overflow-hidden">
      <div
        className={`h-2 rounded-full transition-all ${scoreBarColor(score)}`}
        style={{ width: `${score}%` }}
      />
    </div>
    <span className={`text-sm font-bold w-8 text-right ${scoreColor(score)}`}>{score}</span>
  </div>
)

interface BlindSpotCardProps {
  topic: TopicScore
  onCatchup: (topic: string) => void
  catchupLoading: boolean
  catchupBrief: CatchupBrief | null
}

const BlindSpotCard = ({ topic, onCatchup, catchupLoading, catchupBrief }: BlindSpotCardProps) => (
  <div className="bg-amber-900/20 border border-amber-500/30 rounded-xl p-5">
    <div className="flex items-start justify-between gap-4 mb-3">
      <h3 className="text-gray-100 font-bold text-lg">{topic.topic}</h3>
      <span className={`text-2xl font-bold flex-shrink-0 ${scoreColor(topic.avg_score)}`}>
        {topic.avg_score}
      </span>
    </div>

    <div className="mb-3">
      <div className="bg-gray-700 rounded-full h-2 overflow-hidden">
        <div
          className="h-2 rounded-full bg-red-500 transition-all"
          style={{ width: `${topic.avg_score}%` }}
        />
      </div>
    </div>

    <p className="text-gray-400 text-xs mb-4">
      {topic.question_count} question{topic.question_count !== 1 ? 's' : ''} across{' '}
      {topic.sessions_appeared_in} session{topic.sessions_appeared_in !== 1 ? 's' : ''}
    </p>

    <button
      onClick={() => onCatchup(topic.topic)}
      disabled={catchupLoading}
      className="inline-flex items-center gap-2 bg-amber-600 hover:bg-amber-500 disabled:bg-amber-800 disabled:cursor-not-allowed text-white font-medium px-4 py-2 rounded-lg transition-colors text-sm"
    >
      {catchupLoading ? 'Generating personalized explanation...' : 'Generate Catch-up Brief'}
    </button>

    {catchupBrief && (
      <div className="mt-4 bg-gray-800 border border-gray-600 rounded-lg p-4">
        <p className="text-xs text-gray-400 uppercase tracking-wider mb-2">Catch-up Brief</p>
        <pre className="text-gray-200 text-sm leading-relaxed whitespace-pre-wrap font-sans">
          {catchupBrief.brief}
        </pre>
        {catchupBrief.source_sessions.length > 0 && (
          <p className="text-xs text-gray-500 mt-3">
            Sources: session{catchupBrief.source_sessions.length !== 1 ? 's' : ''}{' '}
            {catchupBrief.source_sessions.join(', ')}
          </p>
        )}
      </div>
    )}
  </div>
)

interface TrendBarProps {
  point: { session_id: number; title: string; score: number; date: string }
}

const TrendBar = ({ point }: TrendBarProps) => {
  const [hovered, setHovered] = useState(false)

  return (
    <div
      className="relative flex flex-col items-center"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {hovered && (
        <div className="absolute bottom-full mb-2 z-10 bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-xs text-gray-200 whitespace-nowrap pointer-events-none shadow-lg">
          <p className="font-medium">{point.title}</p>
          <p className={`font-bold ${scoreColor(point.score)}`}>Score: {point.score}</p>
          <p className="text-gray-400">
            {new Date(point.date).toLocaleDateString('en-US', {
              month: 'short',
              day: 'numeric',
            })}
          </p>
        </div>
      )}
      <div
        className={`w-8 rounded-t-sm transition-all cursor-pointer ${scoreBarColor(point.score)} ${hovered ? 'opacity-100' : 'opacity-70'}`}
        style={{ height: `${Math.max(point.score, 4)}%` }}
      />
    </div>
  )
}

const AnalyticsPage = () => {
  const [analytics, setAnalytics] = useState<Analytics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [catchupLoading, setCatchupLoading] = useState<string | null>(null)
  const [catchupBriefs, setCatchupBriefs] = useState<Record<string, CatchupBrief>>({})

  useEffect(() => {
    getAnalytics()
      .then(setAnalytics)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Failed to load analytics')
      )
      .finally(() => setLoading(false))
  }, [])

  const handleCatchup = async (topic: string) => {
    setCatchupLoading(topic)
    try {
      const brief = await getCatchup(topic)
      setCatchupBriefs((prev) => ({ ...prev, [topic]: brief }))
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to generate catch-up brief'
      setError(msg)
    } finally {
      setCatchupLoading(null)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        <span className="ml-3 text-gray-400">Loading analytics...</span>
      </div>
    )
  }

  if (error && !analytics) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-10">
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-red-400 text-sm">
          {error}
        </div>
        <Link to="/" className="inline-block mt-4 text-gray-400 hover:text-gray-200 text-sm">
          Back to home
        </Link>
      </div>
    )
  }

  if (!analytics) return null

  const sortedTopics = [...analytics.topic_scores].sort((a, b) => a.avg_score - b.avg_score)

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      {/* Header */}
      <div className="mb-8">
        <Link to="/" className="text-gray-500 hover:text-gray-300 text-sm transition-colors">
          Back to home
        </Link>
        <h1 className="text-3xl font-bold text-gray-100 tracking-tight mt-4">
          Comprehension Analytics
        </h1>
        <p className="text-gray-400 mt-1 text-sm">
          Your learning patterns across all VibeCheck sessions
        </p>
      </div>

      {/* Error banner (non-fatal) */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-red-400 text-sm mb-6">
          {error}
        </div>
      )}

      {/* Empty state */}
      {analytics.completed_sessions === 0 ? (
        <div className="text-center py-20 border border-dashed border-gray-700 rounded-xl">
          <h2 className="text-gray-300 font-semibold text-lg mb-2">No quiz attempts yet</h2>
          <p className="text-gray-500 text-sm mb-6">
            Complete a session quiz to see your analytics.
          </p>
          <Link
            to="/"
            className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-4 py-2 rounded-lg transition-colors text-sm"
          >
            Go to sessions
          </Link>
        </div>
      ) : (
        <>
          {/* Summary row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <StatCard label="Total Sessions" value={analytics.total_sessions} />
            <StatCard label="Completed" value={analytics.completed_sessions} />
            <StatCard label="Questions Answered" value={analytics.total_questions_answered} />
            <StatCard
              label="Overall Avg Score"
              value={analytics.overall_avg_score}
              valueClass={scoreColor(analytics.overall_avg_score)}
            />
          </div>

          {/* Blind Spots */}
          {analytics.blind_spots.length > 0 && (
            <div className="mb-8">
              <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg px-4 py-3 mb-4 flex items-center gap-3">
                <span className="text-amber-400 font-semibold text-sm">
                  You have {analytics.blind_spots.length} blind spot
                  {analytics.blind_spots.length !== 1 ? 's' : ''} — topic
                  {analytics.blind_spots.length !== 1 ? 's' : ''} where you consistently score
                  below 60%
                </span>
              </div>
              <div className="space-y-4">
                {analytics.blind_spots.map((topic) => (
                  <BlindSpotCard
                    key={topic.topic}
                    topic={topic}
                    onCatchup={handleCatchup}
                    catchupLoading={catchupLoading === topic.topic}
                    catchupBrief={catchupBriefs[topic.topic] ?? null}
                  />
                ))}
              </div>
            </div>
          )}

          {/* All Topics */}
          {sortedTopics.length > 0 && (
            <div className="mb-8">
              <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-4">
                All Topics
              </h2>
              <div className="bg-gray-900 border border-gray-700 rounded-xl overflow-hidden">
                {sortedTopics.map((topic, i) => (
                  <div
                    key={topic.topic}
                    className={`flex items-center gap-4 px-5 py-4 ${
                      i !== sortedTopics.length - 1 ? 'border-b border-gray-800' : ''
                    }`}
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-gray-200 text-sm font-medium truncate">{topic.topic}</p>
                      <p className="text-gray-500 text-xs mt-0.5">
                        {topic.question_count} question{topic.question_count !== 1 ? 's' : ''}
                      </p>
                    </div>
                    <ScoreBar score={topic.avg_score} />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Session Score Trend */}
          {analytics.trend.length > 1 && (
            <div className="mb-8">
              <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-4">
                Session Score Trend
              </h2>
              <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
                <div className="flex items-end gap-2 h-32">
                  {analytics.trend.map((point) => (
                    <TrendBar key={point.session_id} point={point} />
                  ))}
                </div>
                <div className="flex items-center gap-4 mt-4 pt-4 border-t border-gray-800">
                  <div className="flex items-center gap-1.5 text-xs text-gray-500">
                    <div className="w-3 h-3 rounded-sm bg-green-500" />
                    75+ Good
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-gray-500">
                    <div className="w-3 h-3 rounded-sm bg-yellow-500" />
                    50–74 Fair
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-gray-500">
                    <div className="w-3 h-3 rounded-sm bg-red-500" />
                    &lt;50 Needs Review
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Overall score ring (shown when we have data) */}
          <div className="text-center mt-6">
            <div
              className={`inline-flex items-center justify-center w-24 h-24 rounded-full border-4 ${scoreBorderColor(analytics.overall_avg_score)}`}
            >
              <span className={`text-3xl font-bold ${scoreColor(analytics.overall_avg_score)}`}>
                {analytics.overall_avg_score}
              </span>
            </div>
            <p className="text-gray-500 text-xs mt-2 uppercase tracking-wider">
              Overall comprehension
            </p>
          </div>
        </>
      )}

      <div className="mt-8 text-center">
        <Link to="/" className="text-gray-500 hover:text-gray-300 text-sm transition-colors">
          Back to sessions
        </Link>
      </div>
    </div>
  )
}

export default AnalyticsPage
