import { useEffect, useRef, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  analyzeSessionHealth,
  getSessionHealth,
  generateHandoff,
  getHandoff,
  applyHandoff,
  SessionHealth as SessionHealthType,
  SessionHandoff,
  LazyPrompt,
  ContextBreakpoint,
} from '../api/sessions'

const efficiencyColor = (score: number): string => {
  if (score >= 80) return 'text-green-400'
  if (score >= 60) return 'text-yellow-400'
  return 'text-red-400'
}

const efficiencyBg = (score: number): string => {
  if (score >= 80) return 'border-green-500/40 bg-green-500/10'
  if (score >= 60) return 'border-yellow-500/40 bg-yellow-500/10'
  return 'border-red-500/40 bg-red-500/10'
}

const efficiencyLabel = (score: number): string => {
  if (score >= 80) return 'Healthy'
  if (score >= 60) return 'Moderate rot'
  return 'Heavy rot'
}

const LazyPromptCard = ({ prompt }: { prompt: LazyPrompt }) => (
  <div className="border border-gray-700 rounded-lg overflow-hidden">
    <div className="flex items-center gap-3 px-4 py-2 bg-gray-800/60 border-b border-gray-700">
      <span className="text-xs text-gray-500 font-mono">msg #{prompt.position}</span>
      <span className="text-xs text-gray-400">{prompt.reason}</span>
    </div>
    <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
      <div>
        <p className="text-xs text-red-400 font-medium uppercase tracking-wider mb-2">What you sent</p>
        <div className="bg-red-500/10 border border-red-500/20 rounded px-3 py-2">
          <p className="text-red-300 font-mono text-sm">&ldquo;{prompt.text}&rdquo;</p>
        </div>
      </div>
      <div>
        <p className="text-xs text-green-400 font-medium uppercase tracking-wider mb-2">Better version</p>
        <div className="bg-green-500/10 border border-green-500/20 rounded px-3 py-2">
          <p className="text-green-300 text-sm">&ldquo;{prompt.suggested_rewrite}&rdquo;</p>
        </div>
      </div>
    </div>
  </div>
)

const BreakpointCard = ({ bp }: { bp: ContextBreakpoint }) => (
  <div className="border border-gray-700 rounded-lg p-4 flex gap-4">
    <div className="flex-shrink-0">
      <div className="w-10 h-10 rounded-full bg-orange-500/20 border border-orange-500/30 flex items-center justify-center">
        <span className="text-orange-400 text-xs font-mono font-bold">#{bp.message_num}</span>
      </div>
    </div>
    <div>
      <p className="text-sm font-medium text-gray-200">{bp.reason}</p>
      <p className="text-xs text-gray-500 mt-1">{bp.context}</p>
    </div>
  </div>
)

const HandoffPanel = ({ sessionId, handoff }: {
  sessionId: number
  handoff: SessionHandoff
}) => {
  const [copied, setCopied] = useState(false)
  const [filePath, setFilePath] = useState('')
  const [writeStatus, setWriteStatus] = useState<string | null>(null)
  const [writing, setWriting] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(handoff.content).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  const handleWrite = async () => {
    if (!filePath.trim()) return
    setWriting(true)
    setWriteStatus(null)
    try {
      await applyHandoff(sessionId, filePath.trim())
      setWriteStatus(`Written to ${filePath.trim()}`)
    } catch (err: unknown) {
      setWriteStatus(err instanceof Error ? err.message : 'Write failed')
    } finally {
      setWriting(false)
    }
  }

  return (
    <div className="border border-indigo-500/30 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 bg-indigo-500/10 border-b border-indigo-500/20">
        <div>
          <span className="text-sm font-medium text-indigo-300">Fresh-Start Handoff</span>
          <span className="ml-2 text-xs text-gray-500">{handoff.word_count} words</span>
        </div>
        <button
          onClick={handleCopy}
          className="text-xs font-medium px-3 py-1.5 rounded-md border border-indigo-500/40 text-indigo-400 hover:bg-indigo-500/20 transition-colors"
        >
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <pre className="p-5 text-sm text-gray-300 font-mono leading-relaxed whitespace-pre-wrap overflow-auto max-h-96 bg-gray-900/60">
        {handoff.content}
      </pre>
      <div className="px-5 py-3 border-t border-gray-800 bg-gray-900/40 flex gap-2">
        <input
          type="text"
          placeholder="/abs/path/to/HANDOFF.md"
          value={filePath}
          onChange={(e) => setFilePath(e.target.value)}
          className="flex-1 bg-gray-800 border border-gray-600 rounded px-3 py-1.5 text-xs text-gray-300 placeholder-gray-600 focus:outline-none focus:border-indigo-500"
        />
        <button
          onClick={handleWrite}
          disabled={writing || !filePath.trim()}
          className="text-xs font-medium px-3 py-1.5 rounded-md bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-gray-300 transition-colors"
        >
          {writing ? 'Writing...' : 'Write to file'}
        </button>
      </div>
      {writeStatus && (
        <p className={`px-5 py-2 text-xs ${writeStatus.startsWith('Written') ? 'text-green-400' : 'text-red-400'}`}>
          {writeStatus}
        </p>
      )}
    </div>
  )
}

const SessionHealth = () => {
  const { id } = useParams<{ id: string }>()
  const sessionId = Number(id)

  const [health, setHealth] = useState<SessionHealthType | null>(null)
  const [handoff, setHandoff] = useState<SessionHandoff | null>(null)
  const [status, setStatus] = useState<'loading' | 'analyzing' | 'ready' | 'error'>('loading')
  const [handoffStatus, setHandoffStatus] = useState<'idle' | 'generating' | 'ready'>('idle')
  const [error, setError] = useState<string | null>(null)
  const handoffRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (isNaN(sessionId)) {
      setError('Invalid session ID')
      setStatus('error')
      return
    }

    const run = async () => {
      // Try to get cached health first
      try {
        const existing = await getSessionHealth(sessionId)
        setHealth(existing)
        setStatus('ready')
        // If rot was detected, also load or auto-generate the handoff
        if (existing.efficiency_score < 70) {
          loadOrGenerateHandoff(existing.efficiency_score)
        }
        return
      } catch {
        // No cached health — auto-analyze now
      }

      setStatus('analyzing')
      try {
        const data = await analyzeSessionHealth(sessionId)
        setHealth(data)
        setStatus('ready')
        if (data.efficiency_score < 70) {
          loadOrGenerateHandoff(data.efficiency_score)
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Analysis failed')
        setStatus('error')
      }
    }

    const loadOrGenerateHandoff = async (_efficiency: number) => {
      // Try cached first
      try {
        const existing = await getHandoff(sessionId)
        setHandoff(existing)
        setHandoffStatus('ready')
        return
      } catch {
        // Not cached — auto-generate
      }

      setHandoffStatus('generating')
      try {
        const h = await generateHandoff(sessionId)
        setHandoff(h)
        setHandoffStatus('ready')
        // Scroll to handoff after generation
        setTimeout(() => handoffRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100)
      } catch {
        setHandoffStatus('idle')
      }
    }

    run()
  }, [sessionId])

  if (status === 'loading' || status === 'analyzing') {
    return (
      <div className="max-w-4xl mx-auto px-4 py-10">
        <div className="mb-6">
          <Link to={`/sessions/${sessionId}`} className="text-gray-500 hover:text-gray-300 text-sm transition-colors">
            ← Back to session
          </Link>
        </div>
        <div className="flex flex-col items-center justify-center py-32 gap-4">
          <div className="w-8 h-8 border-2 border-orange-500 border-t-transparent rounded-full animate-spin" />
          <div className="text-center">
            <p className="text-gray-300 font-medium">
              {status === 'loading' ? 'Loading...' : 'Analyzing context health...'}
            </p>
            {status === 'analyzing' && (
              <p className="text-gray-500 text-sm mt-1">
                Scanning for lazy prompts and token waste patterns. Usually takes 10–15 seconds.
              </p>
            )}
          </div>
        </div>
      </div>
    )
  }

  if (status === 'error' || !health) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-10">
        <Link to={`/sessions/${sessionId}`} className="text-gray-500 hover:text-gray-300 text-sm transition-colors">
          ← Back to session
        </Link>
        <div className="mt-6 bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-red-400 text-sm">
          {error ?? 'Failed to analyze session'}
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      <div className="mb-6">
        <Link to={`/sessions/${sessionId}`} className="text-gray-500 hover:text-gray-300 text-sm transition-colors">
          ← Back to session
        </Link>
      </div>

      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-100">Context Health Report</h1>
        <p className="text-gray-500 text-sm mt-1">
          Measures vague prompts that inflate token costs as conversations grow.
        </p>
      </div>

      {/* Summary stats */}
      <div className={`border rounded-xl p-6 mb-6 ${efficiencyBg(health.efficiency_score)}`}>
        <div className="flex flex-wrap gap-6 items-center">
          <div className="text-center">
            <div className={`text-5xl font-bold ${efficiencyColor(health.efficiency_score)}`}>
              {Math.round(health.efficiency_score)}
            </div>
            <div className="text-xs text-gray-400 mt-1 uppercase tracking-wider">Efficiency</div>
            <div className={`text-xs font-medium mt-1 ${efficiencyColor(health.efficiency_score)}`}>
              {efficiencyLabel(health.efficiency_score)}
            </div>
          </div>
          <div className="flex-1 grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-red-400">{health.lazy_prompt_count}</div>
              <div className="text-xs text-gray-500 mt-1">Lazy prompts</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-200">{health.user_messages}</div>
              <div className="text-xs text-gray-500 mt-1">Your messages</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-200">{health.total_messages}</div>
              <div className="text-xs text-gray-500 mt-1">Total turns</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-orange-400">
                ~{Math.round(health.estimated_wasted_token_ratio * 100)}%
              </div>
              <div className="text-xs text-gray-500 mt-1">Token waste est.</div>
            </div>
          </div>
        </div>
      </div>

      {/* Token inflation bar */}
      {health.total_messages > 0 && (
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-5 mb-6">
          <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">Token Inflation</h2>
          <p className="text-xs text-gray-500 mb-4">
            Each message re-reads all prior history. By message {health.total_messages}, you paid ~{health.total_messages}× the cost of message 1 in re-reads alone.
          </p>
          <div className="relative h-4 bg-gray-800 rounded-full overflow-hidden">
            <div
              className="absolute inset-y-0 left-0 bg-gradient-to-r from-green-600 to-red-600 rounded-full"
              style={{ width: `${Math.min(100, (health.total_messages / 100) * 100)}%` }}
            />
            {health.breakpoints.map((bp) => (
              <div
                key={bp.message_num}
                className="absolute inset-y-0 w-0.5 bg-orange-400/70"
                style={{ left: `${(bp.message_num / health.total_messages) * 100}%` }}
                title={`Suggested break at msg #${bp.message_num}`}
              />
            ))}
          </div>
          <div className="flex justify-between text-xs text-gray-600 mt-1">
            <span>msg 1</span>
            {health.breakpoints.length > 0 && <span className="text-orange-500/70">▲ recommended breaks</span>}
            <span>msg {health.total_messages}</span>
          </div>
        </div>
      )}

      {/* Summary */}
      <div className="bg-gray-900 border border-gray-700 rounded-xl p-5 mb-6">
        <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">Summary</h2>
        <p className="text-gray-300 text-sm leading-relaxed">{health.summary}</p>
      </div>

      {/* Lazy prompts */}
      {health.lazy_prompts.length > 0 && (
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-5 mb-6">
          <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-4">
            Lazy Prompts ({health.lazy_prompt_count})
          </h2>
          <p className="text-xs text-gray-500 mb-4">
            Each one forced the AI to guess your intent from an ever-growing history.
          </p>
          <div className="space-y-3">
            {health.lazy_prompts.map((p, i) => (
              <LazyPromptCard key={i} prompt={p} />
            ))}
          </div>
        </div>
      )}

      {health.lazy_prompts.length === 0 && (
        <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-5 mb-6 text-center">
          <p className="text-green-400 font-medium">No lazy prompts detected</p>
          <p className="text-green-300/60 text-xs mt-1">Every message in this session was specific and actionable.</p>
        </div>
      )}

      {/* Breakpoints */}
      {health.breakpoints.length > 0 && (
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-5 mb-6">
          <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-4">Recommended Breakpoints</h2>
          <p className="text-xs text-gray-500 mb-4">
            Natural topic shifts where starting fresh would have cut re-read cost and improved focus.
          </p>
          <div className="space-y-3">
            {health.breakpoints.map((bp, i) => (
              <BreakpointCard key={i} bp={bp} />
            ))}
          </div>
        </div>
      )}

      {/* Handoff section — only shown when rot is detected */}
      {health.efficiency_score < 70 && (
        <div ref={handoffRef} className="mb-6">
          <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-2">Fresh-Start Handoff</h2>
          <p className="text-xs text-gray-500 mb-4">
            Compressed context (&lt;500 words) from this session. Paste it as the first message in a new Claude Code session to start fresh without losing your place.
          </p>

          {handoffStatus === 'generating' && (
            <div className="border border-indigo-500/20 rounded-xl p-6 flex items-center gap-3 bg-indigo-500/5">
              <div className="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin flex-shrink-0" />
              <p className="text-sm text-indigo-300">Compressing session into handoff document...</p>
            </div>
          )}

          {handoffStatus === 'ready' && handoff && (
            <HandoffPanel sessionId={sessionId} handoff={handoff} />
          )}
        </div>
      )}

      <div className="text-center mt-6">
        <p className="text-xs text-gray-600">Report generated {new Date(health.created_at).toLocaleDateString()}</p>
      </div>
    </div>
  )
}

export default SessionHealth
