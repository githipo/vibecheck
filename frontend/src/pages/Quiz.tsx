import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { getQuiz, submitAttempt, Quiz as QuizType, Question } from '../api/sessions'

interface Answer {
  question_id: number
  answer_text: string
}

const QuestionCard = ({
  question,
  answer,
  onAnswer,
  index,
  total,
}: {
  question: Question
  answer: string
  onAnswer: (text: string) => void
  index: number
  total: number
}) => {
  const isMultipleChoice = question.type === 'multiple_choice' && question.choices && question.choices.length > 0

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl p-6">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-xs font-medium text-indigo-400 uppercase tracking-wider">
          {question.type === 'multiple_choice'
            ? 'Multiple Choice'
            : question.type === 'short_answer'
            ? 'Short Answer'
            : 'Code Explanation'}
        </span>
        <span className="text-gray-600 text-xs">•</span>
        <span className="text-gray-500 text-xs">
          Question {index + 1} of {total}
        </span>
      </div>

      <p className="text-gray-100 text-base leading-relaxed mb-6">{question.question}</p>

      {isMultipleChoice && question.choices ? (
        <div className="space-y-2">
          {question.choices.map((choice, i) => (
            <label
              key={i}
              className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                answer === choice
                  ? 'border-indigo-500 bg-indigo-500/10 text-gray-100'
                  : 'border-gray-700 hover:border-gray-500 text-gray-300'
              }`}
            >
              <input
                type="radio"
                name={`question-${question.id}`}
                value={choice}
                checked={answer === choice}
                onChange={() => onAnswer(choice)}
                className="mt-0.5 accent-indigo-500 flex-shrink-0"
              />
              <span className="text-sm leading-relaxed">{choice}</span>
            </label>
          ))}
        </div>
      ) : (
        <textarea
          value={answer}
          onChange={(e) => onAnswer(e.target.value)}
          placeholder={
            question.type === 'code_explanation'
              ? 'Explain what this code does and why it was written this way...'
              : 'Your answer...'
          }
          rows={6}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-gray-100 placeholder-gray-500 text-sm font-mono focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors resize-y"
        />
      )}
    </div>
  )
}

const Quiz = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const sessionId = Number(id)

  const [quiz, setQuiz] = useState<QuizType | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [answers, setAnswers] = useState<Record<number, string>>({})
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  useEffect(() => {
    if (isNaN(sessionId)) {
      setError('Invalid session ID')
      setLoading(false)
      return
    }
    getQuiz(sessionId)
      .then(setQuiz)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : 'Failed to load quiz'))
      .finally(() => setLoading(false))
  }, [sessionId])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        <span className="ml-3 text-gray-400">Loading quiz...</span>
      </div>
    )
  }

  if (error || !quiz) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-10">
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-red-400 text-sm">
          {error ?? 'Quiz not found'}
        </div>
        <Link to={`/sessions/${sessionId}`} className="inline-block mt-4 text-gray-400 hover:text-gray-200 text-sm">
          ← Back to session
        </Link>
      </div>
    )
  }

  const questions = quiz.questions
  const total = questions.length
  const currentQuestion: Question | undefined = questions[currentIndex]
  const progress = ((currentIndex + 1) / total) * 100
  const currentAnswer = currentQuestion ? (answers[currentQuestion.id] ?? '') : ''
  const isLast = currentIndex === total - 1
  const canProceed = currentAnswer.trim().length > 0

  const handleAnswer = (text: string) => {
    if (!currentQuestion) return
    setAnswers((prev) => ({ ...prev, [currentQuestion.id]: text }))
  }

  const handleNext = () => {
    if (currentIndex < total - 1) {
      setCurrentIndex((prev) => prev + 1)
    }
  }

  const handleBack = () => {
    if (currentIndex > 0) {
      setCurrentIndex((prev) => prev - 1)
    }
  }

  const handleSubmit = async () => {
    setSubmitError(null)
    setSubmitting(true)
    const answerList: Answer[] = questions.map((q) => ({
      question_id: q.id,
      answer_text: answers[q.id] ?? '',
    }))
    try {
      await submitAttempt(sessionId, answerList)
      navigate(`/sessions/${sessionId}/results`)
    } catch (err: unknown) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to submit answers')
      setSubmitting(false)
    }
  }

  if (!currentQuestion) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-10">
        <div className="text-gray-400">No questions found in this quiz.</div>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-10">
      <div className="mb-6">
        <Link
          to={`/sessions/${sessionId}`}
          className="text-gray-500 hover:text-gray-300 text-sm transition-colors"
        >
          ← Back to session
        </Link>
      </div>

      <div className="flex items-center justify-between mb-2">
        <h1 className="text-xl font-bold text-gray-100">Quiz</h1>
        <span className="text-gray-500 text-sm">
          {currentIndex + 1} / {total}
        </span>
      </div>

      <div className="w-full bg-gray-800 rounded-full h-1.5 mb-8">
        <div
          className="bg-indigo-500 h-1.5 rounded-full transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>

      <QuestionCard
        question={currentQuestion}
        answer={currentAnswer}
        onAnswer={handleAnswer}
        index={currentIndex}
        total={total}
      />

      {submitError && (
        <div className="mt-4 bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-red-400 text-sm">
          {submitError}
        </div>
      )}

      <div className="flex items-center justify-between mt-6">
        <button
          onClick={handleBack}
          disabled={currentIndex === 0}
          className="text-sm text-gray-400 hover:text-gray-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors px-3 py-2"
        >
          ← Previous
        </button>

        <div className="flex items-center gap-2">
          {questions.map((_, i) => (
            <button
              key={i}
              onClick={() => setCurrentIndex(i)}
              className={`w-2 h-2 rounded-full transition-colors ${
                i === currentIndex
                  ? 'bg-indigo-500'
                  : answers[questions[i]?.id ?? -1]?.trim()
                  ? 'bg-gray-500'
                  : 'bg-gray-700'
              }`}
            />
          ))}
        </div>

        {isLast ? (
          <button
            onClick={handleSubmit}
            disabled={submitting || !canProceed}
            className="inline-flex items-center gap-2 bg-green-700 hover:bg-green-600 disabled:opacity-60 disabled:cursor-not-allowed text-white font-medium px-5 py-2 rounded-lg transition-colors text-sm"
          >
            {submitting ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Evaluating...
              </>
            ) : (
              'Submit Answers'
            )}
          </button>
        ) : (
          <button
            onClick={handleNext}
            disabled={!canProceed}
            className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 disabled:cursor-not-allowed text-white font-medium px-5 py-2 rounded-lg transition-colors text-sm"
          >
            Next →
          </button>
        )}
      </div>
    </div>
  )
}

export default Quiz
