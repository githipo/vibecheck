import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  generateSelfBrief,
  applySelfBrief,
  SelfBriefResult,
  AIBrief,
  SuggestedAgent,
} from '../api/sessions'
import { Spinner, BriefResults } from './SelfBriefComponents'

// ── Apply Panel ───────────────────────────────────────────────────────────────

interface ApplyPanelProps {
  brief: AIBrief
  suggestedAgents: SuggestedAgent[]
}

const ApplyPanel = ({ brief, suggestedAgents }: ApplyPanelProps) => {
  const [filePath, setFilePath] = useState('')
  const [includeAgents, setIncludeAgents] = useState(true)
  const [applying, setApplying] = useState(false)
  const [applyError, setApplyError] = useState<string | null>(null)
  const [applyResult, setApplyResult] = useState<{
    applied: boolean
    file_path: string
    chars_added: number
  } | null>(null)

  const handleApply = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!filePath.trim()) return
    setApplying(true)
    setApplyError(null)
    setApplyResult(null)
    try {
      const result = await applySelfBrief(filePath.trim(), brief, suggestedAgents, includeAgents)
      setApplyResult(result)
    } catch (err: unknown) {
      setApplyError(err instanceof Error ? err.message : 'Failed to apply brief')
    } finally {
      setApplying(false)
    }
  }

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl p-5 mt-6">
      <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-4">
        Apply to CLAUDE.md
      </h2>

      <form onSubmit={handleApply} className="space-y-4">
        <div>
          <label className="block text-xs text-gray-400 mb-1.5">CLAUDE.md file path (absolute)</label>
          <input
            type="text"
            value={filePath}
            onChange={(e) => setFilePath(e.target.value)}
            placeholder="/Users/you/project/CLAUDE.md"
            className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-2.5 text-gray-200 text-sm placeholder-gray-500 focus:outline-none focus:border-indigo-500 font-mono"
          />
        </div>

        <label className="flex items-center gap-3 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={includeAgents}
            onChange={(e) => setIncludeAgents(e.target.checked)}
            className="w-4 h-4 accent-indigo-500"
          />
          <span className="text-sm text-gray-300">Include sub-agent definitions</span>
        </label>

        {applyError && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2 text-red-400 text-sm">
            {applyError}
          </div>
        )}

        {applyResult && (
          <div className="bg-green-500/10 border border-green-500/30 rounded-lg px-3 py-2 text-green-400 text-sm">
            Applied successfully to{' '}
            <span className="font-mono text-xs">{applyResult.file_path}</span> —{' '}
            {applyResult.chars_added} characters added.
          </div>
        )}

        <button
          type="submit"
          disabled={applying || !filePath.trim()}
          className="bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-900 disabled:cursor-not-allowed text-white font-medium px-4 py-2.5 rounded-lg transition-colors text-sm"
        >
          {applying ? 'Applying...' : 'Apply'}
        </button>
      </form>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

const SelfBrief = () => {
  const [directory, setDirectory] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<SelfBriefResult | null>(null)

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!directory.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await generateSelfBrief(directory.trim())
      setResult(data)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to generate brief')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      {/* Header */}
      <div className="mb-8">
        <Link to="/" className="text-gray-500 hover:text-gray-300 text-sm transition-colors">
          Back to home
        </Link>
        <h1 className="text-3xl font-bold text-gray-100 tracking-tight mt-4">AI Self-Brief</h1>
        <p className="text-gray-400 mt-1 text-sm">
          Generate an AI-readable brief of your codebase — architecture, conventions, invariants,
          and suggested sub-agents
        </p>
      </div>

      {/* Input panel */}
      <div className="bg-gray-900 border border-gray-700 rounded-xl p-5 mb-6">
        <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-4">
          Analyze a directory
        </h2>
        <form onSubmit={handleGenerate} className="flex gap-3">
          <input
            type="text"
            value={directory}
            onChange={(e) => setDirectory(e.target.value)}
            placeholder="/Users/you/project"
            className="flex-1 bg-gray-800 border border-gray-600 rounded-lg px-4 py-2.5 text-gray-200 text-sm placeholder-gray-500 focus:outline-none focus:border-indigo-500 font-mono"
          />
          <button
            type="submit"
            disabled={loading || !directory.trim()}
            className="bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-900 disabled:cursor-not-allowed text-white font-medium px-4 py-2.5 rounded-lg transition-colors text-sm whitespace-nowrap"
          >
            {loading ? 'Analyzing...' : 'Generate AI Brief'}
          </button>
        </form>
        {loading && <Spinner label="Analyzing codebase..." />}
        {error && (
          <div className="mt-3 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2 text-red-400 text-sm">
            {error}
          </div>
        )}
      </div>

      {/* Empty state */}
      {!loading && !result && !error && (
        <div className="text-center py-16 border border-dashed border-gray-700 rounded-xl">
          <p className="text-gray-500 text-sm">
            Enter a directory path above and click Generate AI Brief.
          </p>
        </div>
      )}

      {/* Results */}
      {result && (
        <>
          <div className="flex items-center gap-2 mb-5">
            <p className="text-gray-400 text-sm">
              Brief for{' '}
              <span className="font-mono text-gray-300 text-xs">{result.directory}</span>
            </p>
            <span className="text-gray-600 text-xs">
              &middot; generated {new Date(result.generated_at).toLocaleString()}
            </span>
          </div>

          <BriefResults brief={result.brief} agents={result.suggested_agents} />
          <ApplyPanel brief={result.brief} suggestedAgents={result.suggested_agents} />
        </>
      )}
    </div>
  )
}

export default SelfBrief
