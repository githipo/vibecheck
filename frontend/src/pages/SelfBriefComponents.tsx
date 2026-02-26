import { useState } from 'react'
import { AIBrief, SuggestedAgent, KeyEntryPoint } from '../api/sessions'

// ── Spinner ──────────────────────────────────────────────────────────────────

export const Spinner = ({ label }: { label: string }) => (
  <div className="flex items-center gap-2 text-gray-400 text-sm mt-3">
    <div className="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
    {label}
  </div>
)

// ── Section heading ───────────────────────────────────────────────────────────

export const SectionHeading = ({ children }: { children: React.ReactNode }) => (
  <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">
    {children}
  </h2>
)

// ── BulletList ────────────────────────────────────────────────────────────────

interface BulletListProps {
  items: string[]
  itemClass?: string
  markerClass?: string
}

export const BulletList = ({
  items,
  itemClass = 'text-gray-300',
  markerClass = 'text-indigo-400',
}: BulletListProps) => (
  <ul className="space-y-1.5">
    {items.map((item, i) => (
      <li key={i} className="flex items-start gap-2">
        <span className={`mt-1 text-xs leading-none flex-shrink-0 ${markerClass}`}>&#9679;</span>
        <span className={`text-sm leading-relaxed ${itemClass}`}>{item}</span>
      </li>
    ))}
  </ul>
)

// ── EntryPointsTable ──────────────────────────────────────────────────────────

export const EntryPointsTable = ({ points }: { points: KeyEntryPoint[] }) => (
  <div className="overflow-x-auto">
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-gray-700">
          <th className="text-left text-gray-400 text-xs uppercase tracking-wider pb-2 pr-6 font-medium">
            File
          </th>
          <th className="text-left text-gray-400 text-xs uppercase tracking-wider pb-2 font-medium">
            Role
          </th>
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-800">
        {points.map((point, i) => (
          <tr key={i}>
            <td className="py-2 pr-6 font-mono text-xs text-indigo-300 align-top">
              {point.file}
            </td>
            <td className="py-2 text-gray-300 text-xs align-top">{point.role}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
)

// ── CopyButton ────────────────────────────────────────────────────────────────

export const CopyButton = ({ text }: { text: string }) => {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <button
      onClick={handleCopy}
      className="text-xs border border-gray-600 hover:border-gray-400 text-gray-400 hover:text-gray-200 px-2 py-1 rounded transition-colors"
    >
      {copied ? 'Copied!' : 'Copy'}
    </button>
  )
}

// ── AgentCard ─────────────────────────────────────────────────────────────────

interface AgentCardProps {
  agent: SuggestedAgent
}

export const AgentCard = ({ agent }: AgentCardProps) => {
  const [showPrompt, setShowPrompt] = useState(false)
  const [showEntry, setShowEntry] = useState(false)

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
      <div className="flex items-start justify-between gap-3 mb-2">
        <div>
          <h3 className="text-gray-100 font-semibold text-base">{agent.name}</h3>
          <span className="text-xs text-indigo-400 font-mono">{agent.role}</span>
        </div>
      </div>
      <p className="text-gray-400 text-sm mb-4">{agent.description}</p>

      <div className="space-y-2">
        <button
          onClick={() => setShowPrompt((v) => !v)}
          className="text-xs border border-gray-600 hover:border-indigo-500 text-gray-400 hover:text-indigo-300 px-3 py-1.5 rounded-lg transition-colors"
        >
          {showPrompt ? 'Hide System Prompt' : 'View System Prompt'}
        </button>
        {showPrompt && (
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 mt-2">
            <pre className="text-gray-300 text-xs leading-relaxed whitespace-pre-wrap font-mono">
              {agent.system_prompt}
            </pre>
          </div>
        )}

        <div>
          <button
            onClick={() => setShowEntry((v) => !v)}
            className="text-xs border border-gray-600 hover:border-indigo-500 text-gray-400 hover:text-indigo-300 px-3 py-1.5 rounded-lg transition-colors"
          >
            {showEntry ? 'Hide CLAUDE.md entry' : 'View CLAUDE.md entry'}
          </button>
          {showEntry && (
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 mt-2">
              <div className="flex justify-end mb-2">
                <CopyButton text={agent.claude_md_entry} />
              </div>
              <pre className="text-gray-300 text-xs leading-relaxed whitespace-pre-wrap font-mono">
                {agent.claude_md_entry}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ── BriefResults ──────────────────────────────────────────────────────────────

interface BriefResultsProps {
  brief: AIBrief
  agents: SuggestedAgent[]
}

export const BriefResults = ({ brief, agents }: BriefResultsProps) => (
  <div className="space-y-6">
    {/* Architecture */}
    <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
      <SectionHeading>Architecture</SectionHeading>
      <p className="text-gray-300 text-sm leading-relaxed">{brief.architecture_summary}</p>
    </div>

    {/* Non-Obvious Conventions */}
    {brief.non_obvious_conventions.length > 0 && (
      <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
        <SectionHeading>Non-Obvious Conventions</SectionHeading>
        <BulletList items={brief.non_obvious_conventions} />
      </div>
    )}

    {/* Critical Invariants */}
    {brief.critical_invariants.length > 0 && (
      <div className="bg-amber-900/20 border border-amber-500/30 rounded-xl p-5">
        <SectionHeading>Critical Invariants</SectionHeading>
        <BulletList
          items={brief.critical_invariants}
          itemClass="text-amber-200"
          markerClass="text-amber-400"
        />
      </div>
    )}

    {/* Common AI Mistakes to Avoid */}
    {brief.common_mistakes_to_avoid.length > 0 && (
      <div className="bg-red-900/15 border border-red-500/30 rounded-xl p-5">
        <SectionHeading>Common AI Mistakes to Avoid</SectionHeading>
        <BulletList
          items={brief.common_mistakes_to_avoid}
          itemClass="text-red-200"
          markerClass="text-red-400"
        />
      </div>
    )}

    {/* Key Entry Points */}
    {brief.key_entry_points.length > 0 && (
      <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
        <SectionHeading>Key Entry Points</SectionHeading>
        <EntryPointsTable points={brief.key_entry_points} />
      </div>
    )}

    {/* Suggested Sub-Agents */}
    {agents.length > 0 && (
      <div>
        <SectionHeading>Suggested Sub-Agents</SectionHeading>
        <div className="space-y-4">
          {agents.map((agent, i) => (
            <AgentCard key={i} agent={agent} />
          ))}
        </div>
      </div>
    )}
  </div>
)
