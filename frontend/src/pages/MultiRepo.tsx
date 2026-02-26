import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  listRepoGroups,
  getRepoGroup,
  deleteRepoGroup,
  analyzeRepoGroup,
  RepoGroupOut,
  RepoGroupDetail,
  RepoContextOut,
} from '../api/sessions'
import {
  Spinner,
  GroupListItem,
  NewGroupForm,
  RepoCard,
  AnalysisResults,
} from './MultiRepoComponents'

// ── Detail panel ──────────────────────────────────────────────────────────────

interface DetailPanelProps {
  groupId: number
  onDeleted: () => void
}

const DetailPanel = ({ groupId, onDeleted }: DetailPanelProps) => {
  const [detail, setDetail] = useState<RepoGroupDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(true)
  const [detailError, setDetailError] = useState<string | null>(null)

  const [analyzing, setAnalyzing] = useState(false)
  const [analyzeError, setAnalyzeError] = useState<string | null>(null)
  const [context, setContext] = useState<RepoContextOut | null>(null)

  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  useEffect(() => {
    setDetailLoading(true)
    setDetailError(null)
    setContext(null)
    setAnalyzeError(null)
    setDeleteConfirm(false)
    getRepoGroup(groupId)
      .then(setDetail)
      .catch((err: unknown) =>
        setDetailError(err instanceof Error ? err.message : 'Failed to load group')
      )
      .finally(() => setDetailLoading(false))
  }, [groupId])

  const handleAnalyze = async () => {
    setAnalyzing(true)
    setAnalyzeError(null)
    try {
      const result = await analyzeRepoGroup(groupId)
      setContext(result)
    } catch (err: unknown) {
      setAnalyzeError(err instanceof Error ? err.message : 'Analysis failed')
    } finally {
      setAnalyzing(false)
    }
  }

  const handleDelete = async () => {
    setDeleting(true)
    setDeleteError(null)
    try {
      await deleteRepoGroup(groupId)
      onDeleted()
    } catch (err: unknown) {
      setDeleteError(err instanceof Error ? err.message : 'Delete failed')
      setDeleting(false)
    }
  }

  if (detailLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Spinner label="Loading group..." />
      </div>
    )
  }

  if (detailError || !detail) {
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-red-400 text-sm">
        {detailError ?? 'Group not found'}
      </div>
    )
  }

  return (
    <div>
      {/* Group header */}
      <div className="mb-5">
        <h2 className="text-xl font-bold text-gray-100">{detail.name}</h2>
        {detail.description && (
          <p className="text-gray-400 text-sm mt-1">{detail.description}</p>
        )}
      </div>

      {/* Repos */}
      {detail.repos.length > 0 && (
        <div className="mb-5">
          <p className="text-xs text-gray-400 uppercase tracking-wider mb-2">
            Repos ({detail.repos.length})
          </p>
          <div className="space-y-2">
            {detail.repos.map((repo) => (
              <RepoCard key={repo.id} repo={repo} />
            ))}
          </div>
        </div>
      )}

      {/* Analyze button */}
      <div className="mb-2">
        <button
          onClick={handleAnalyze}
          disabled={analyzing}
          className="bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-900 disabled:cursor-not-allowed text-white font-medium px-4 py-2.5 rounded-lg transition-colors text-sm"
        >
          {analyzing ? 'Scanning...' : 'Analyze Connections'}
        </button>
      </div>

      {analyzing && (
        <div className="mt-3">
          <Spinner label="Scanning repos and detecting connections..." />
        </div>
      )}

      {analyzeError && (
        <div className="mt-3 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2 text-red-400 text-sm">
          {analyzeError}
        </div>
      )}

      {/* Analysis results */}
      {context && <AnalysisResults context={context} repos={detail.repos} />}

      {/* Delete */}
      <div className="mt-8 pt-6 border-t border-gray-800">
        {deleteError && (
          <div className="mb-3 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2 text-red-400 text-sm">
            {deleteError}
          </div>
        )}
        {deleteConfirm ? (
          <div className="flex items-center gap-3">
            <span className="text-gray-400 text-sm">Are you sure?</span>
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="text-sm bg-red-700 hover:bg-red-600 disabled:bg-red-900 text-white px-3 py-1.5 rounded-lg transition-colors"
            >
              {deleting ? 'Deleting...' : 'Yes, delete'}
            </button>
            <button
              onClick={() => setDeleteConfirm(false)}
              className="text-sm text-gray-500 hover:text-gray-300 transition-colors"
            >
              Cancel
            </button>
          </div>
        ) : (
          <button
            onClick={() => setDeleteConfirm(true)}
            className="text-sm text-gray-600 hover:text-red-400 transition-colors"
          >
            Delete group
          </button>
        )}
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

const MultiRepo = () => {
  const [groups, setGroups] = useState<RepoGroupOut[]>([])
  const [groupsLoading, setGroupsLoading] = useState(true)
  const [groupsError, setGroupsError] = useState<string | null>(null)

  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [showNewForm, setShowNewForm] = useState(false)

  const loadGroups = () => {
    setGroupsLoading(true)
    setGroupsError(null)
    listRepoGroups()
      .then(setGroups)
      .catch((err: unknown) =>
        setGroupsError(err instanceof Error ? err.message : 'Failed to load groups')
      )
      .finally(() => setGroupsLoading(false))
  }

  useEffect(() => {
    loadGroups()
  }, [])

  const handleCreated = (group: RepoGroupOut) => {
    setShowNewForm(false)
    loadGroups()
    setSelectedId(group.id)
  }

  const handleDeleted = () => {
    setSelectedId(null)
    loadGroups()
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-10">
      {/* Header */}
      <div className="mb-8">
        <Link to="/" className="text-gray-500 hover:text-gray-300 text-sm transition-colors">
          Back to home
        </Link>
        <h1 className="text-3xl font-bold text-gray-100 tracking-tight mt-4">
          Multi-Repo Awareness
        </h1>
        <p className="text-gray-400 mt-1 text-sm">
          Group related repositories and analyze how they connect to each other
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Groups list */}
        <div className="lg:col-span-1 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider">
              Repo Groups
            </h2>
            <button
              onClick={() => {
                setShowNewForm((v) => !v)
                setSelectedId(null)
              }}
              className="text-xs bg-indigo-700 hover:bg-indigo-600 text-white px-3 py-1.5 rounded-lg transition-colors"
            >
              {showNewForm ? 'Cancel' : '+ New Group'}
            </button>
          </div>

          {groupsError && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2 text-red-400 text-xs">
              {groupsError}
            </div>
          )}

          {groupsLoading ? (
            <div className="py-4">
              <Spinner label="Loading groups..." />
            </div>
          ) : groups.length === 0 && !showNewForm ? (
            <div className="text-center py-10 border border-dashed border-gray-700 rounded-xl">
              <p className="text-gray-500 text-sm">No repo groups yet.</p>
              <button
                onClick={() => setShowNewForm(true)}
                className="mt-3 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
              >
                Create your first group
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              {groups.map((group) => (
                <GroupListItem
                  key={group.id}
                  group={group}
                  isSelected={selectedId === group.id}
                  onClick={() => {
                    setSelectedId(group.id)
                    setShowNewForm(false)
                  }}
                />
              ))}
            </div>
          )}
        </div>

        {/* Right: Detail / form */}
        <div className="lg:col-span-2">
          {showNewForm ? (
            <NewGroupForm onCreated={handleCreated} onCancel={() => setShowNewForm(false)} />
          ) : selectedId !== null ? (
            <div className="bg-gray-900 border border-gray-700 rounded-xl p-6">
              <DetailPanel
                key={selectedId}
                groupId={selectedId}
                onDeleted={handleDeleted}
              />
            </div>
          ) : (
            <div className="text-center py-20 border border-dashed border-gray-700 rounded-xl">
              <p className="text-gray-500 text-sm">Select a group to see its details.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default MultiRepo
