import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  scanDirectory,
  getFocusAreas,
  addFocusArea,
  removeFocusArea,
  startCodeQuiz,
  FileRisk,
  ScanResult,
  FocusArea,
} from '../api/sessions'

const SHOW_DEFAULT = 10

const riskBadgeClass = (score: number): string => {
  if (score >= 70) return 'bg-red-600 text-white'
  if (score >= 40) return 'bg-amber-500 text-white'
  return 'bg-green-600 text-white'
}

const riskRowTint = (score: number, isFocus: boolean): string => {
  if (isFocus) return 'border-l-4 border-indigo-500 bg-indigo-900/10'
  if (score >= 70) return 'border-l-4 border-red-700 bg-red-900/10'
  return ''
}

const LANG_BADGE: Record<string, string> = {
  py: 'bg-blue-600/30 text-blue-300 border border-blue-500/40',
  ts: 'bg-violet-600/30 text-violet-300 border border-violet-500/40',
  tsx: 'bg-violet-600/30 text-violet-300 border border-violet-500/40',
  js: 'bg-yellow-600/30 text-yellow-300 border border-yellow-500/40',
  jsx: 'bg-yellow-600/30 text-yellow-300 border border-yellow-500/40',
}

const langBadgeClass = (lang: string): string =>
  LANG_BADGE[lang.toLowerCase()] ??
  'bg-gray-700/50 text-gray-300 border border-gray-600/40'

interface RiskBadgeProps {
  score: number
}

const RiskBadge = ({ score }: RiskBadgeProps) => (
  <div
    className={`flex items-center justify-center w-10 h-10 rounded-lg font-bold text-base flex-shrink-0 ${riskBadgeClass(score)}`}
  >
    {score}
  </div>
)

interface PinFormProps {
  prefillPath: string
  onAdd: () => void
}

const PinForm = ({ prefillPath, onAdd }: PinFormProps) => {
  const [label, setLabel] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      await addFocusArea({ type: 'file', value: prefillPath, label: label || prefillPath })
      onAdd()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to pin')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2 mt-2">
      <input
        type="text"
        value={label}
        onChange={(e) => setLabel(e.target.value)}
        placeholder="Display name (optional)"
        className="flex-1 bg-gray-800 border border-gray-600 rounded-lg px-3 py-1.5 text-gray-200 text-xs placeholder-gray-500 focus:outline-none focus:border-indigo-500"
      />
      {error && <span className="text-red-400 text-xs">{error}</span>}
      <button
        type="submit"
        disabled={loading}
        className="text-xs bg-indigo-700 hover:bg-indigo-600 disabled:bg-indigo-900 text-white px-3 py-1.5 rounded-lg transition-colors"
      >
        {loading ? 'Pinning...' : 'Pin'}
      </button>
    </form>
  )
}

interface FileRowProps {
  file: FileRisk
  onQuiz: (path: string) => void
  quizLoading: boolean
  onFocusAdded: () => void
}

const FileRow = ({ file, onQuiz, quizLoading, onFocusAdded }: FileRowProps) => {
  const [showPinForm, setShowPinForm] = useState(false)

  const handlePinAdded = () => {
    setShowPinForm(false)
    onFocusAdded()
  }

  return (
    <div
      className={`bg-gray-900 border border-gray-700 rounded-xl px-4 py-4 ${riskRowTint(file.risk_score, file.is_focus)}`}
    >
      <div className="flex items-start gap-3">
        <RiskBadge score={file.risk_score} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            {file.is_focus && (
              <span className="text-indigo-400 text-base leading-none" title="Focus area">
                🎯
              </span>
            )}
            <span className="text-gray-100 font-bold text-sm truncate">{file.relative_path}</span>
            <span
              className={`text-xs px-2 py-0.5 rounded-md font-mono ${langBadgeClass(file.language)}`}
            >
              {file.language}
            </span>
          </div>
          <p className="text-gray-500 text-xs mt-1">
            {file.line_count} lines · {file.import_count} imports
          </p>
          {file.blast_radius && (
            <p className="text-gray-500 text-xs italic mt-0.5">{file.blast_radius}</p>
          )}
          {file.risk_factors.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {file.risk_factors.map((factor) => (
                <span
                  key={factor}
                  className="bg-gray-800 border border-gray-600 text-gray-400 text-xs px-2 py-0.5 rounded-md"
                >
                  {factor}
                </span>
              ))}
            </div>
          )}
          {showPinForm && (
            <div className="mt-2">
              <PinForm prefillPath={file.path} onAdd={handlePinAdded} />
            </div>
          )}
        </div>
        <div className="flex flex-col gap-2 flex-shrink-0">
          <button
            onClick={() => onQuiz(file.path)}
            disabled={quizLoading}
            className="text-xs bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-900 disabled:cursor-not-allowed text-white px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap"
          >
            {quizLoading ? 'Starting...' : 'Quiz me on this'}
          </button>
          {!file.is_focus && (
            <button
              onClick={() => setShowPinForm((v) => !v)}
              className="text-xs border border-gray-600 hover:border-indigo-500 text-gray-400 hover:text-indigo-300 px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap"
            >
              {showPinForm ? 'Cancel' : 'Pin as Focus'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

interface FocusAreaItemProps {
  area: FocusArea
  onRemove: (id: number) => void
}

const FocusAreaItem = ({ area, onRemove }: FocusAreaItemProps) => (
  <div className="flex items-start justify-between gap-3 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5">
    <div className="flex-1 min-w-0">
      <div className="flex items-center gap-2">
        <span className="text-xs bg-indigo-900/50 text-indigo-300 border border-indigo-700/40 px-1.5 py-0.5 rounded font-mono">
          {area.type}
        </span>
        <span className="text-gray-200 text-sm font-medium truncate">{area.label}</span>
      </div>
      <p className="text-gray-500 text-xs mt-0.5 truncate font-mono">{area.value}</p>
    </div>
    <button
      onClick={() => onRemove(area.id)}
      className="text-gray-500 hover:text-red-400 transition-colors text-sm leading-none flex-shrink-0 mt-0.5"
      title="Remove focus area"
    >
      ×
    </button>
  </div>
)

const CodebaseMap = () => {
  const navigate = useNavigate()

  const [directory, setDirectory] = useState('')
  const [scanResult, setScanResult] = useState<ScanResult | null>(null)
  const [scanning, setScanning] = useState(false)
  const [scanError, setScanError] = useState<string | null>(null)
  const [showAll, setShowAll] = useState(false)

  const [focusAreas, setFocusAreas] = useState<FocusArea[]>([])
  const [focusLoading, setFocusLoading] = useState(true)
  const [focusError, setFocusError] = useState<string | null>(null)

  const [addType, setAddType] = useState<'file' | 'concept'>('file')
  const [addValue, setAddValue] = useState('')
  const [addLabel, setAddLabel] = useState('')
  const [addLoading, setAddLoading] = useState(false)
  const [addError, setAddError] = useState<string | null>(null)

  const [quizLoading, setQuizLoading] = useState<string | null>(null)

  const loadFocusAreas = () => {
    setFocusLoading(true)
    getFocusAreas()
      .then(setFocusAreas)
      .catch((err: unknown) =>
        setFocusError(err instanceof Error ? err.message : 'Failed to load focus areas')
      )
      .finally(() => setFocusLoading(false))
  }

  useEffect(() => {
    loadFocusAreas()
  }, [])

  const handleScan = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!directory.trim()) return
    setScanning(true)
    setScanError(null)
    setScanResult(null)
    setShowAll(false)
    try {
      const result = await scanDirectory(directory.trim())
      setScanResult(result)
    } catch (err: unknown) {
      setScanError(err instanceof Error ? err.message : 'Scan failed')
    } finally {
      setScanning(false)
    }
  }

  const handleAddFocus = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!addValue.trim() || !addLabel.trim()) return
    setAddLoading(true)
    setAddError(null)
    try {
      await addFocusArea({ type: addType, value: addValue.trim(), label: addLabel.trim() })
      setAddValue('')
      setAddLabel('')
      loadFocusAreas()
    } catch (err: unknown) {
      setAddError(err instanceof Error ? err.message : 'Failed to add focus area')
    } finally {
      setAddLoading(false)
    }
  }

  const handleRemoveFocus = async (id: number) => {
    try {
      await removeFocusArea(id)
      loadFocusAreas()
    } catch (err: unknown) {
      setFocusError(err instanceof Error ? err.message : 'Failed to remove focus area')
    }
  }

  const handleQuiz = async (filePath: string) => {
    setQuizLoading(filePath)
    try {
      const session = await startCodeQuiz(filePath)
      navigate(`/sessions/${session.id}/quiz`)
    } catch (err: unknown) {
      setScanError(err instanceof Error ? err.message : 'Failed to start quiz')
      setQuizLoading(null)
    }
  }

  const displayedFiles = scanResult
    ? showAll
      ? scanResult.files
      : scanResult.files.slice(0, SHOW_DEFAULT)
    : []

  return (
    <div className="max-w-5xl mx-auto px-4 py-10">
      {/* Header */}
      <div className="mb-8">
        <Link to="/" className="text-gray-500 hover:text-gray-300 text-sm transition-colors">
          Back to home
        </Link>
        <h1 className="text-3xl font-bold text-gray-100 tracking-tight mt-4">Codebase Map</h1>
        <p className="text-gray-400 mt-1 text-sm">
          Find the parts of your codebase you might not fully understand
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column: Scan + Results */}
        <div className="lg:col-span-2 space-y-6">
          {/* Scan Panel */}
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
            <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-4">
              Scan a directory
            </h2>
            <form onSubmit={handleScan} className="flex gap-3">
              <input
                type="text"
                value={directory}
                onChange={(e) => setDirectory(e.target.value)}
                placeholder="/Users/you/project/src"
                className="flex-1 bg-gray-800 border border-gray-600 rounded-lg px-4 py-2.5 text-gray-200 text-sm placeholder-gray-500 focus:outline-none focus:border-indigo-500 font-mono"
              />
              <button
                type="submit"
                disabled={scanning || !directory.trim()}
                className="bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-900 disabled:cursor-not-allowed text-white font-medium px-4 py-2.5 rounded-lg transition-colors text-sm whitespace-nowrap"
              >
                {scanning ? 'Scanning...' : 'Scan'}
              </button>
            </form>
            {scanning && (
              <div className="flex items-center gap-2 mt-3 text-gray-400 text-sm">
                <div className="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                Scanning and assessing risk...
              </div>
            )}
            {scanError && (
              <div className="mt-3 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2 text-red-400 text-sm">
                {scanError}
              </div>
            )}
          </div>

          {/* Scan Results */}
          {scanResult ? (
            <div>
              <div className="flex items-center justify-between mb-4">
                <p className="text-gray-300 text-sm">
                  <span className="font-bold text-gray-100">{scanResult.file_count}</span> files
                  scanned in{' '}
                  <span className="font-mono text-gray-400 text-xs">{scanResult.root}</span>
                </p>
              </div>

              {/* Risk legend */}
              <div className="flex items-center gap-4 mb-4 bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5">
                <span className="text-gray-500 text-xs uppercase tracking-wider">Risk:</span>
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded-sm bg-red-600" />
                  <span className="text-xs text-gray-400">70–100 High</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded-sm bg-amber-500" />
                  <span className="text-xs text-gray-400">40–69 Medium</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded-sm bg-green-600" />
                  <span className="text-xs text-gray-400">0–39 Low</span>
                </div>
              </div>

              {scanResult.files.length === 0 ? (
                <div className="text-center py-12 border border-dashed border-gray-700 rounded-xl">
                  <p className="text-gray-500 text-sm">No files found in that directory.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {displayedFiles.map((file) => (
                    <FileRow
                      key={file.path}
                      file={file}
                      onQuiz={handleQuiz}
                      quizLoading={quizLoading === file.path}
                      onFocusAdded={loadFocusAreas}
                    />
                  ))}
                  {scanResult.files.length > SHOW_DEFAULT && (
                    <button
                      onClick={() => setShowAll((v) => !v)}
                      className="w-full text-center text-sm text-gray-500 hover:text-gray-300 py-3 border border-dashed border-gray-700 rounded-xl transition-colors"
                    >
                      {showAll
                        ? 'Show fewer'
                        : `Show all ${scanResult.files.length} files`}
                    </button>
                  )}
                </div>
              )}
            </div>
          ) : (
            !scanning && (
              <div className="text-center py-16 border border-dashed border-gray-700 rounded-xl">
                <p className="text-gray-500 text-sm">
                  Enter a directory path above and click Scan.
                </p>
              </div>
            )
          )}
        </div>

        {/* Right column: Focus Areas */}
        <div className="space-y-4">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
            <div className="flex items-center gap-2 mb-4">
              <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider">
                Focus Areas
              </h2>
              <span
                className="text-gray-600 text-xs cursor-default"
                title="Pin files or concepts you always want tracked"
              >
                (?)
              </span>
            </div>

            {focusError && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2 text-red-400 text-xs mb-3">
                {focusError}
              </div>
            )}

            {focusLoading ? (
              <div className="flex items-center gap-2 text-gray-500 text-sm py-2">
                <div className="w-4 h-4 border-2 border-gray-600 border-t-transparent rounded-full animate-spin" />
                Loading...
              </div>
            ) : focusAreas.length === 0 ? (
              <p className="text-gray-600 text-xs mb-4">No focus areas yet.</p>
            ) : (
              <div className="space-y-2 mb-4">
                {focusAreas.map((area) => (
                  <FocusAreaItem key={area.id} area={area} onRemove={handleRemoveFocus} />
                ))}
              </div>
            )}

            {/* Add focus area form */}
            <div className="border-t border-gray-700 pt-4">
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">
                Add Focus Area
              </p>
              <form onSubmit={handleAddFocus} className="space-y-2">
                <select
                  value={addType}
                  onChange={(e) => setAddType(e.target.value as 'file' | 'concept')}
                  className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-gray-300 text-sm focus:outline-none focus:border-indigo-500"
                >
                  <option value="file">File</option>
                  <option value="concept">Concept</option>
                </select>
                <input
                  type="text"
                  value={addValue}
                  onChange={(e) => setAddValue(e.target.value)}
                  placeholder={
                    addType === 'file' ? '/abs/path/file.py' : 'async patterns'
                  }
                  className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-gray-200 text-sm placeholder-gray-500 focus:outline-none focus:border-indigo-500 font-mono"
                />
                <input
                  type="text"
                  value={addLabel}
                  onChange={(e) => setAddLabel(e.target.value)}
                  placeholder="Display name"
                  className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-gray-200 text-sm placeholder-gray-500 focus:outline-none focus:border-indigo-500"
                />
                {addError && (
                  <p className="text-red-400 text-xs">{addError}</p>
                )}
                <button
                  type="submit"
                  disabled={addLoading || !addValue.trim() || !addLabel.trim()}
                  className="w-full bg-indigo-700 hover:bg-indigo-600 disabled:bg-indigo-900 disabled:cursor-not-allowed text-white font-medium px-3 py-2 rounded-lg transition-colors text-sm"
                >
                  {addLoading ? 'Adding...' : 'Add'}
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default CodebaseMap
