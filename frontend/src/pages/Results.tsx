import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { getResults, getQuiz, Attempt, Quiz, Question } from '../api/sessions'

const VERDICT_STYLES: Record<string, string> = {
  correct: 'bg-green-500/20 text-green-400 border border-green-500/30',
  partial: 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30',
  incorrect: 'bg-red-500/20 text-red-400 border border-red-500/30',
}

const VERDICT_LABELS: Record<string, string> = {
  correct: 'Correct',
  partial: 'Partial',
  incorrect: 'Incorrect',
}

const scoreColor = (score: number): string => {
  if (score >= 75) return 'text-green-400'
  if (score >= 50) return 'text-yellow-400'
  return 'text-red-400'
}

const scoreRingColor = (score: number): string => {
  if (score >= 75) return 'border-green-500'
  if (score >= 50) return 'border-yellow-500'
  return 'border-red-500'
}

const scoreLabel = (score: number): string => {
  if (score >= 90) return 'Excellent'
  if (score >= 75) return 'Good'
  if (score >= 50) return 'Fair'
  return 'Needs Review'
}

const Results = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const sessionId = Number(id)

  const [attempt, setAttempt] = useState<Attempt | null>(null)
  const [quiz, setQuiz] = useState<Quiz | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (isNaN(sessionId)) {
      setError('Invalid session ID')
      setLoading(false)
      return
    }

    Promise.all([getResults(sessionId), getQuiz(sessionId)])
      .then(([attemptData, quizData]) => {
        setAttempt(attemptData)
        setQuiz(quizData)
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : 'Failed to load results'))
      .finally(() => setLoading(false))
  }, [sessionId])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        <span className="ml-3 text-gray-400">Loading results...</span>
      </div>
    )
  }

  if (error || !attempt) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-10">
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-red-400 text-sm">
          {error ?? 'Results not found'}
        </div>
        <Link to={`/sessions/${sessionId}`} className="inline-block mt-4 text-gray-400 hover:text-gray-200 text-sm">
          ← Back to session
        </Link>
      </div>
    )
  }

  const questionMap = new Map<number, Question>()
  if (quiz) {
    for (const q of quiz.questions) {
      questionMap.set(q.id, q)
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-10">
      <div className="mb-6">
        <Link to="/" className="text-gray-500 hover:text-gray-300 text-sm transition-colors">
          ← Back to sessions
        </Link>
      </div>

      <div className="bg-gray-900 border border-gray-700 rounded-xl p-8 mb-6 text-center">
        <p className="text-gray-400 text-sm uppercase tracking-widest mb-4">Your Score</p>
        <div
          className={`inline-flex items-center justify-center w-32 h-32 rounded-full border-4 mb-4 ${scoreRingColor(attempt.score)}`}
        >
          <span className={`text-5xl font-bold ${scoreColor(attempt.score)}`}>{attempt.score}</span>
        </div>
        <div className={`text-lg font-semibold mb-4 ${scoreColor(attempt.score)}`}>
          {scoreLabel(attempt.score)}
        </div>
        <p className="text-gray-300 text-sm leading-relaxed max-w-lg mx-auto">
          {attempt.feedback_summary}
        </p>

        <div className="flex items-center justify-center gap-3 mt-6">
          <button
            onClick={() => navigate(`/sessions/${sessionId}/quiz`)}
            className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-4 py-2 rounded-lg transition-colors text-sm"
          >
            Retake Quiz
          </button>
          <Link
            to={`/sessions/${sessionId}`}
            className="inline-flex items-center gap-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 text-gray-300 font-medium px-4 py-2 rounded-lg transition-colors text-sm"
          >
            View Session
          </Link>
        </div>
      </div>

      <div className="space-y-4">
        <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider">Question Breakdown</h2>

        {attempt.evaluations.map((evaluation, i) => {
          const question = questionMap.get(evaluation.question_id)
          return (
            <div
              key={evaluation.question_id}
              className="bg-gray-900 border border-gray-700 rounded-xl p-5"
            >
              <div className="flex items-start justify-between gap-4 mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-gray-500 text-xs font-mono">Q{i + 1}</span>
                  {question && (
                    <span className="text-xs text-indigo-400 uppercase tracking-wider">
                      {question.type === 'multiple_choice'
                        ? 'Multiple Choice'
                        : question.type === 'short_answer'
                        ? 'Short Answer'
                        : 'Code Explanation'}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span
                    className={`text-xs px-2 py-0.5 rounded-md font-medium ${VERDICT_STYLES[evaluation.verdict] ?? 'bg-gray-700 text-gray-300'}`}
                  >
                    {VERDICT_LABELS[evaluation.verdict] ?? evaluation.verdict}
                  </span>
                  <span className={`text-sm font-bold ${scoreColor(evaluation.score)}`}>
                    {evaluation.score}
                  </span>
                </div>
              </div>

              {question && (
                <p className="text-gray-200 text-sm leading-relaxed mb-3">{question.question}</p>
              )}

              <div className="bg-gray-800/60 border border-gray-700 rounded-lg px-3 py-2.5 mb-3">
                <p className="text-xs text-gray-500 mb-1">Your answer</p>
                <p className="text-gray-300 text-sm leading-relaxed font-mono whitespace-pre-wrap">
                  {/* We don't have the submitted answer text in the Attempt model here, so we rely on feedback */}
                  {evaluation.feedback.startsWith('Your answer')
                    ? evaluation.feedback
                    : <span className="text-gray-500 italic">See feedback below</span>}
                </p>
              </div>

              <div className="flex gap-2">
                <div
                  className={`w-0.5 rounded-full flex-shrink-0 self-stretch ${
                    evaluation.verdict === 'correct'
                      ? 'bg-green-500/50'
                      : evaluation.verdict === 'partial'
                      ? 'bg-yellow-500/50'
                      : 'bg-red-500/50'
                  }`}
                />
                <div>
                  <p className="text-xs text-gray-500 mb-1">Feedback</p>
                  <p className="text-gray-300 text-sm leading-relaxed">{evaluation.feedback}</p>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      <div className="mt-6 text-center">
        <Link to="/" className="text-gray-500 hover:text-gray-300 text-sm transition-colors">
          ← Back to all sessions
        </Link>
      </div>
    </div>
  )
}

export default Results
