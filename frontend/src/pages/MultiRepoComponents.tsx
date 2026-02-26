import { useState } from 'react'
import {
  RepoGroupOut,
  RepoOut,
  RepoConnectionOut,
  RepoContextOut,
  RepoIn,
  createRepoGroup,
} from '../api/sessions'

// ── Spinner ───────────────────────────────────────────────────────────────────

export const Spinner = ({ label }: { label: string }) => (
  <div className="flex items-center gap-2 text-gray-400 text-sm">
    <div className="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
    {label}
  </div>
)

// ── Role badge ────────────────────────────────────────────────────────────────

const ROLE_COLORS: Record<string, string> = {
  frontend: 'bg-violet-600/30 text-violet-300 border border-violet-500/40',
  backend: 'bg-blue-600/30 text-blue-300 border border-blue-500/40',
  sdk: 'bg-emerald-600/30 text-emerald-300 border border-emerald-500/40',
  app: 'bg-teal-600/30 text-teal-300 border border-teal-500/40',
  microservice: 'bg-amber-600/30 text-amber-300 border border-amber-500/40',
  other: 'bg-gray-700/50 text-gray-300 border border-gray-600/40',
}

export const RoleBadge = ({ role }: { role: string }) => (
  <span
    className={`text-xs px-2 py-0.5 rounded-md font-mono flex-shrink-0 ${ROLE_COLORS[role] ?? ROLE_COLORS.other}`}
  >
    {role}
  </span>
)

// ── Connection type badge ─────────────────────────────────────────────────────

const CONNECTION_COLORS: Record<string, string> = {
  api_call: 'bg-blue-600/30 text-blue-300 border border-blue-500/40',
  shared_type: 'bg-purple-600/30 text-purple-300 border border-purple-500/40',
  package_dependency: 'bg-green-600/30 text-green-300 border border-green-500/40',
  event: 'bg-orange-600/30 text-orange-300 border border-orange-500/40',
}

export const ConnectionBadge = ({ type }: { type: string }) => (
  <span
    className={`text-xs px-2 py-0.5 rounded-md font-mono flex-shrink-0 ${CONNECTION_COLORS[type] ?? 'bg-gray-700/50 text-gray-300 border border-gray-600/40'}`}
  >
    {type}
  </span>
)

// ── Repo mini-card ────────────────────────────────────────────────────────────

export const RepoCard = ({ repo }: { repo: RepoOut }) => (
  <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 flex items-start gap-3">
    <RoleBadge role={repo.role} />
    <div className="flex-1 min-w-0">
      <p className="text-gray-200 text-sm font-medium">{repo.name}</p>
      <p className="text-gray-500 text-xs mt-0.5 font-mono truncate">{repo.path}</p>
    </div>
  </div>
)

// ── Connection row ────────────────────────────────────────────────────────────

interface ConnectionRowProps {
  connection: RepoConnectionOut
  repos: RepoOut[]
}

export const ConnectionRow = ({ connection, repos }: ConnectionRowProps) => {
  const fromRepo = repos.find((r) => r.id === connection.from_repo_id)
  const toRepo = repos.find((r) => r.id === connection.to_repo_id)

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl px-4 py-4">
      <div className="flex items-center gap-3 flex-wrap mb-2">
        <span className="text-gray-200 text-sm font-medium">
          {fromRepo?.name ?? `repo #${connection.from_repo_id}`}
        </span>
        <span className="text-gray-500 text-sm">&#8594;</span>
        <span className="text-gray-200 text-sm font-medium">
          {toRepo?.name ?? `repo #${connection.to_repo_id}`}
        </span>
        <ConnectionBadge type={connection.connection_type} />
      </div>
      <p className="text-gray-400 text-sm">{connection.description}</p>
      {connection.evidence && (
        <p className="text-gray-600 text-xs font-mono mt-1">{connection.evidence}</p>
      )}
    </div>
  )
}

// ── Group list item ───────────────────────────────────────────────────────────

interface GroupListItemProps {
  group: RepoGroupOut
  isSelected: boolean
  onClick: () => void
}

export const GroupListItem = ({ group, isSelected, onClick }: GroupListItemProps) => (
  <button
    onClick={onClick}
    className={`w-full text-left bg-gray-900 border rounded-xl px-4 py-3 transition-all ${
      isSelected
        ? 'border-indigo-500 bg-indigo-900/10'
        : 'border-gray-700 hover:border-gray-500 hover:bg-gray-800'
    }`}
  >
    <p className="text-gray-100 font-medium text-sm">{group.name}</p>
    {group.description && (
      <p className="text-gray-500 text-xs mt-0.5 line-clamp-1">{group.description}</p>
    )}
    <p className="text-gray-600 text-xs mt-1.5">
      {group.repos.length} repo{group.repos.length !== 1 ? 's' : ''} &middot;{' '}
      {new Date(group.created_at).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
      })}
    </p>
  </button>
)

// ── New group form ────────────────────────────────────────────────────────────

const ROLE_OPTIONS = ['frontend', 'backend', 'sdk', 'app', 'microservice', 'other'] as const

interface NewRepoRow {
  name: string
  path: string
  role: string
}

const emptyRow = (): NewRepoRow => ({ name: '', path: '', role: 'frontend' })

interface NewGroupFormProps {
  onCreated: (group: RepoGroupOut) => void
  onCancel: () => void
}

export const NewGroupForm = ({ onCreated, onCancel }: NewGroupFormProps) => {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [rows, setRows] = useState<NewRepoRow[]>([emptyRow()])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const updateRow = (index: number, field: keyof NewRepoRow, value: string) => {
    setRows((prev) => prev.map((row, i) => (i === index ? { ...row, [field]: value } : row)))
  }

  const addRow = () => setRows((prev) => [...prev, emptyRow()])
  const removeRow = (index: number) => setRows((prev) => prev.filter((_, i) => i !== index))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    const validRepos: RepoIn[] = rows
      .filter((r) => r.name.trim() && r.path.trim())
      .map((r) => ({ name: r.name.trim(), path: r.path.trim(), role: r.role }))
    setLoading(true)
    setError(null)
    try {
      const group = await createRepoGroup(name.trim(), description.trim(), validRepos)
      onCreated(group)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create group')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-gray-200 font-semibold text-base">New Repo Group</h3>
        <button
          onClick={onCancel}
          className="text-gray-500 hover:text-gray-300 text-sm transition-colors"
        >
          Cancel
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Group name"
          className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-gray-200 text-sm placeholder-gray-500 focus:outline-none focus:border-indigo-500"
        />
        <input
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Description (optional)"
          className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-gray-200 text-sm placeholder-gray-500 focus:outline-none focus:border-indigo-500"
        />

        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Repos</p>
          <div className="space-y-2">
            {rows.map((row, i) => (
              <div key={i} className="flex gap-2 items-start">
                <input
                  type="text"
                  value={row.name}
                  onChange={(e) => updateRow(i, 'name', e.target.value)}
                  placeholder="Name"
                  className="w-24 bg-gray-800 border border-gray-600 rounded-lg px-2 py-1.5 text-gray-200 text-xs placeholder-gray-500 focus:outline-none focus:border-indigo-500"
                />
                <input
                  type="text"
                  value={row.path}
                  onChange={(e) => updateRow(i, 'path', e.target.value)}
                  placeholder="/abs/path"
                  className="flex-1 bg-gray-800 border border-gray-600 rounded-lg px-2 py-1.5 text-gray-200 text-xs placeholder-gray-500 focus:outline-none focus:border-indigo-500 font-mono"
                />
                <select
                  value={row.role}
                  onChange={(e) => updateRow(i, 'role', e.target.value)}
                  className="bg-gray-800 border border-gray-600 rounded-lg px-2 py-1.5 text-gray-300 text-xs focus:outline-none focus:border-indigo-500"
                >
                  {ROLE_OPTIONS.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
                {rows.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeRow(i)}
                    className="text-gray-600 hover:text-red-400 text-sm transition-colors leading-none pt-1.5"
                  >
                    ×
                  </button>
                )}
              </div>
            ))}
          </div>
          <button
            type="button"
            onClick={addRow}
            className="mt-2 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
          >
            + Add Repo
          </button>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2 text-red-400 text-xs">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading || !name.trim()}
          className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-900 disabled:cursor-not-allowed text-white font-medium px-3 py-2 rounded-lg transition-colors text-sm"
        >
          {loading ? 'Creating...' : 'Create Group'}
        </button>
      </form>
    </div>
  )
}

// ── Analysis results ──────────────────────────────────────────────────────────

interface AnalysisResultsProps {
  context: RepoContextOut
  repos: RepoOut[]
}

export const AnalysisResults = ({ context, repos }: AnalysisResultsProps) => (
  <div className="space-y-5 mt-5">
    {/* Summary */}
    <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
      <p className="text-xs text-gray-400 uppercase tracking-wider mb-2">Summary</p>
      <p className="text-gray-300 text-sm leading-relaxed">{context.summary}</p>
    </div>

    {/* Repo Briefs */}
    {Object.keys(context.repo_briefs).length > 0 && (
      <div>
        <p className="text-xs text-gray-400 uppercase tracking-wider mb-3">Repo Briefs</p>
        <div className="space-y-2">
          {Object.entries(context.repo_briefs).map(([repoName, brief]) => (
            <div
              key={repoName}
              className="bg-gray-900 border border-gray-700 rounded-lg px-4 py-3"
            >
              <p className="text-gray-200 text-sm font-medium mb-0.5">{repoName}</p>
              <p className="text-gray-400 text-xs">{brief}</p>
            </div>
          ))}
        </div>
      </div>
    )}

    {/* Connections */}
    {context.connections.length > 0 && (
      <div>
        <p className="text-xs text-gray-400 uppercase tracking-wider mb-3">
          Connections ({context.connections.length})
        </p>
        <div className="space-y-3">
          {context.connections.map((conn) => (
            <ConnectionRow key={conn.id} connection={conn} repos={repos} />
          ))}
        </div>
      </div>
    )}

    {context.connections.length === 0 && (
      <div className="text-center py-8 border border-dashed border-gray-700 rounded-xl">
        <p className="text-gray-500 text-sm">No cross-repo connections detected.</p>
      </div>
    )}
  </div>
)
