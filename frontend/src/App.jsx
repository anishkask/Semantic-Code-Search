import { useState } from 'react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { atomDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

function App() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [results, setResults] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    setError(null)
    setResults(null)

    try {
      const res = await fetch(`${API_URL}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query.trim(),
          n_results: 5,
          model: 'local',
        }),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || `Request failed: ${res.status}`)
      }

      const data = await res.json()
      setResults(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>Semantic Code Search</h1>
        <form onSubmit={handleSubmit} className="search-form">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search the codebase..."
            className="search-input"
            disabled={loading}
          />
          <button type="submit" className="search-btn" disabled={loading}>
            {loading ? 'Searching...' : 'Search'}
          </button>
        </form>
      </header>

      <main className="main">
        {error && (
          <div className="error">
            {error}
          </div>
        )}

        {loading && (
          <div className="loading">Searching...</div>
        )}

        {results && !loading && (
          <div className="results">
            <p className="results-meta">
              {results.count} result{results.count !== 1 ? 's' : ''} for "{results.query}"
            </p>
            {results.results.map((r, i) => (
              <ResultCard key={i} result={r} />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

function ResultCard({ result }) {
  const typeClass = result.type ? `badge-${result.type}` : ''
  const lineRange = result.start_line && result.end_line
    ? `${result.start_line}–${result.end_line}`
    : result.start_line
      ? `${result.start_line}`
      : ''

  return (
    <article className="result-card">
      <div className="result-header">
        <span className="result-name">{result.name}</span>
        {result.type && (
          <span className={`badge ${typeClass}`}>{result.type}</span>
        )}
        {result.distance != null && (
          <span className="distance">distance: {result.distance.toFixed(4)}</span>
        )}
      </div>
      <div className="result-meta">
        <span className="file-path">{result.file_path}</span>
        {lineRange && <span className="line-range">lines {lineRange}</span>}
        {result.parent_class && (
          <span className="parent-class">in {result.parent_class}</span>
        )}
      </div>
      <div className="code-block">
        <div className="code-header">
          {result.file_path && <span>{result.file_path}</span>}
          {lineRange && <span>lines {lineRange}</span>}
        </div>
        <SyntaxHighlighter
          language="python"
          style={atomDark}
          customStyle={{ margin: 0, borderRadius: '0 0 6px 6px' }}
          codeTagProps={{ style: { fontSize: '13px' } }}
        >
          {result.source || ''}
        </SyntaxHighlighter>
      </div>
    </article>
  )
}

export default App
