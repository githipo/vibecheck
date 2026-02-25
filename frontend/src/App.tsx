import { Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import NewSession from './pages/NewSession'
import SessionDetail from './pages/SessionDetail'
import Quiz from './pages/Quiz'
import Results from './pages/Results'
import Insights from './pages/Insights'
import Analytics from './pages/Analytics'
import CodebaseMap from './pages/CodebaseMap'

const App = () => {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/sessions/new" element={<NewSession />} />
        <Route path="/sessions/:id" element={<SessionDetail />} />
        <Route path="/sessions/:id/quiz" element={<Quiz />} />
        <Route path="/sessions/:id/results" element={<Results />} />
        <Route path="/sessions/:id/insights" element={<Insights />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/codebase" element={<CodebaseMap />} />
      </Routes>
    </div>
  )
}

export default App
