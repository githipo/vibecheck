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
