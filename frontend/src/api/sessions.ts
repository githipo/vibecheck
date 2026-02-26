export interface Session {
  id: number
  title: string
  source_type: string
  status: string
  created_at: string
}

export interface SessionDetail extends Session {
  transcript: string
}

export interface Question {
  id: number
  type: string
  question: string
  choices?: string[]
}

export interface Quiz {
  id: number
  session_id: number
  questions: Question[]
  created_at: string
}

export interface EvaluationResult {
  question_id: number
  verdict: string
  score: number
  feedback: string
}

export interface Attempt {
  id: number
  session_id: number
  quiz_id: number
  score: number
  feedback_summary: string
  evaluations: EvaluationResult[]
  created_at: string
}

interface CreateSessionData {
  title: string
  transcript: string
  source_type: string
}

interface AnswerData {
  question_id: number
  answer_text: string
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`HTTP ${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

export const createSession = async (data: CreateSessionData): Promise<Session> => {
  const res = await fetch('/api/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return handleResponse<Session>(res)
}

export const listSessions = async (): Promise<Session[]> => {
  const res = await fetch('/api/sessions')
  return handleResponse<Session[]>(res)
}

export const getSession = async (id: number): Promise<SessionDetail> => {
  const res = await fetch(`/api/sessions/${id}`)
  return handleResponse<SessionDetail>(res)
}

export const deleteSession = async (id: number): Promise<void> => {
  const res = await fetch(`/api/sessions/${id}`, { method: 'DELETE' })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`HTTP ${res.status}: ${text}`)
  }
}

export const generateQuiz = async (sessionId: number): Promise<Quiz> => {
  const res = await fetch(`/api/sessions/${sessionId}/quiz`, { method: 'POST' })
  return handleResponse<Quiz>(res)
}

export const getQuiz = async (sessionId: number): Promise<Quiz> => {
  const res = await fetch(`/api/sessions/${sessionId}/quiz`)
  return handleResponse<Quiz>(res)
}

export const submitAttempt = async (
  sessionId: number,
  answers: AnswerData[]
): Promise<Attempt> => {
  const res = await fetch(`/api/sessions/${sessionId}/attempt`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ answers }),
  })
  return handleResponse<Attempt>(res)
}

export const getResults = async (sessionId: number): Promise<Attempt> => {
  const res = await fetch(`/api/sessions/${sessionId}/results`)
  return handleResponse<Attempt>(res)
}

export interface Decision {
  decision: string
  rationale: string
  alternatives_rejected: string[]
}

export interface Pattern {
  pattern: string
  description: string
}

export interface Gotcha {
  issue: string
  context: string
}

export interface ProposedRule {
  rule: string
  rationale: string
  section: string
}

export interface Insight {
  id: number
  session_id: number
  decisions: Decision[]
  patterns: Pattern[]
  gotchas: Gotcha[]
  proposed_rules: ProposedRule[]
  created_at: string
}

export const generateInsights = async (sessionId: number): Promise<Insight> => {
  const res = await fetch(`/api/sessions/${sessionId}/insights`, { method: 'POST' })
  if (res.status === 409) {
    return getInsights(sessionId)
  }
  return handleResponse<Insight>(res)
}

export const getInsights = async (sessionId: number): Promise<Insight> => {
  const res = await fetch(`/api/sessions/${sessionId}/insights`)
  return handleResponse<Insight>(res)
}

export const applyInsights = async (
  sessionId: number,
  filePath: string
): Promise<{ applied: boolean; file_path: string; chars_added: number }> => {
  const res = await fetch(`/api/sessions/${sessionId}/insights/apply`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_path: filePath }),
  })
  return handleResponse<{ applied: boolean; file_path: string; chars_added: number }>(res)
}

export interface TopicScore {
  topic: string
  avg_score: number
  question_count: number
  sessions_appeared_in: number
  is_blind_spot: boolean
}

export interface TrendPoint {
  session_id: number
  title: string
  score: number
  date: string
}

export interface Analytics {
  total_sessions: number
  completed_sessions: number
  total_questions_answered: number
  overall_avg_score: number
  topic_scores: TopicScore[]
  blind_spots: TopicScore[]
  trend: TrendPoint[]
}

export interface CatchupBrief {
  topic: string
  brief: string
  source_sessions: number[]
}

export const getAnalytics = async (): Promise<Analytics> => {
  const res = await fetch('/api/analytics')
  return handleResponse<Analytics>(res)
}

export const getCatchup = async (topic: string): Promise<CatchupBrief> => {
  const res = await fetch('/api/analytics/catchup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic }),
  })
  return handleResponse<CatchupBrief>(res)
}

export interface FileRisk {
  path: string
  relative_path: string
  language: string
  line_count: number
  import_count: number
  risk_score: number
  risk_factors: string[]
  blast_radius: string
  is_focus: boolean
}

export interface ScanResult {
  root: string
  file_count: number
  files: FileRisk[]
}

export interface FocusArea {
  id: number
  type: string
  value: string
  label: string
  created_at: string
}

interface AddFocusAreaData {
  type: string
  value: string
  label: string
}

export const scanDirectory = async (
  directory: string,
  extensions?: string[]
): Promise<ScanResult> => {
  const res = await fetch('/api/codebase/scan', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ directory, extensions }),
  })
  return handleResponse<ScanResult>(res)
}

export const getFocusAreas = async (): Promise<FocusArea[]> => {
  const res = await fetch('/api/focus')
  return handleResponse<FocusArea[]>(res)
}

export const addFocusArea = async (data: AddFocusAreaData): Promise<FocusArea> => {
  const res = await fetch('/api/focus', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return handleResponse<FocusArea>(res)
}

export const removeFocusArea = async (id: number): Promise<void> => {
  const res = await fetch(`/api/focus/${id}`, { method: 'DELETE' })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`HTTP ${res.status}: ${text}`)
  }
}

export const startCodeQuiz = async (filePath: string, title?: string): Promise<Session> => {
  const res = await fetch('/api/codebase/quiz', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_path: filePath, title }),
  })
  return handleResponse<Session>(res)
}

// AI Self-Brief types and API calls

export interface KeyEntryPoint {
  file: string
  role: string
}

export interface AIBrief {
  architecture_summary: string
  non_obvious_conventions: string[]
  critical_invariants: string[]
  common_mistakes_to_avoid: string[]
  key_entry_points: KeyEntryPoint[]
}

export interface SuggestedAgent {
  name: string
  role: string
  description: string
  system_prompt: string
  claude_md_entry: string
}

export interface SelfBriefResult {
  directory: string
  brief: AIBrief
  suggested_agents: SuggestedAgent[]
  generated_at: string
}

export const generateSelfBrief = async (directory: string): Promise<SelfBriefResult> => {
  const res = await fetch('/api/codebase/brief', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ directory }),
  })
  return handleResponse<SelfBriefResult>(res)
}

export const applySelfBrief = async (
  filePath: string,
  brief: AIBrief,
  suggestedAgents: SuggestedAgent[],
  includeAgents: boolean
): Promise<{ applied: boolean; file_path: string; chars_added: number }> => {
  const res = await fetch('/api/codebase/brief/apply', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      file_path: filePath,
      brief,
      suggested_agents: suggestedAgents,
      include_agents: includeAgents,
    }),
  })
  return handleResponse<{ applied: boolean; file_path: string; chars_added: number }>(res)
}

// Multi-Repo types and API calls

export interface RepoIn {
  name: string
  path: string
  role: string
}

export interface RepoOut {
  id: number
  group_id: number
  name: string
  path: string
  role: string
  created_at: string
}

export interface RepoConnectionOut {
  id: number
  from_repo_id: number
  to_repo_id: number
  connection_type: string
  description: string
  evidence: string
  created_at: string
}

export interface RepoGroupOut {
  id: number
  name: string
  description: string
  created_at: string
  repos: RepoOut[]
}

export interface RepoGroupDetail extends RepoGroupOut {
  connections: RepoConnectionOut[]
}

export interface RepoContextOut {
  group_name: string
  summary: string
  connections: RepoConnectionOut[]
  repo_briefs: Record<string, string>
}

export const listRepoGroups = async (): Promise<RepoGroupOut[]> => {
  const res = await fetch('/api/repos/groups')
  return handleResponse<RepoGroupOut[]>(res)
}

export const createRepoGroup = async (
  name: string,
  description: string,
  repos: RepoIn[]
): Promise<RepoGroupOut> => {
  const res = await fetch('/api/repos/groups', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description, repos }),
  })
  return handleResponse<RepoGroupOut>(res)
}

export const getRepoGroup = async (id: number): Promise<RepoGroupDetail> => {
  const res = await fetch(`/api/repos/groups/${id}`)
  return handleResponse<RepoGroupDetail>(res)
}

export const deleteRepoGroup = async (id: number): Promise<void> => {
  const res = await fetch(`/api/repos/groups/${id}`, { method: 'DELETE' })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`HTTP ${res.status}: ${text}`)
  }
}

export const analyzeRepoGroup = async (id: number): Promise<RepoContextOut> => {
  const res = await fetch(`/api/repos/groups/${id}/analyze`, { method: 'POST' })
  return handleResponse<RepoContextOut>(res)
}

export const getRepoContext = async (id: number): Promise<RepoContextOut> => {
  const res = await fetch(`/api/repos/groups/${id}/context`)
  return handleResponse<RepoContextOut>(res)
}
