import { useEffect, useMemo, useState } from 'react'
import './App.css'

import {
  executePlan,
  fetchDocuments,
  fetchHealth,
  searchKnowledge,
  sendChatMessage,
  uploadDocument,
} from './api'

const INITIAL_CHAT_MESSAGE = 'Расскажите, какие данные или расчёты вам нужны.'

function usePersistentUserId() {
  return useMemo(() => {
    const storageKey = 'alfa-pilot-user-id'
    const stored = window.localStorage.getItem(storageKey)
    if (stored) {
      return stored
    }
    const uuid = window.crypto && typeof window.crypto.randomUUID === 'function'
      ? window.crypto.randomUUID()
      : Math.random().toString(36).slice(2)
    const generated = uuid
    window.localStorage.setItem(storageKey, generated)
    return generated
  }, [])
}

function App() {
  const userId = usePersistentUserId()
  const [documents, setDocuments] = useState([])
  const [chatInput, setChatInput] = useState('')
  const [chatHistory, setChatHistory] = useState([
    { role: 'system', content: INITIAL_CHAT_MESSAGE },
  ])
  const [pendingPlan, setPendingPlan] = useState(null)
  const [knowledgeHits, setKnowledgeHits] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [healthStatus, setHealthStatus] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [searchResults, setSearchResults] = useState(null)
  const [docUploadProgress, setDocUploadProgress] = useState('')

  useEffect(() => {
    fetchHealth().then(setHealthStatus).catch(() => setHealthStatus({ status: 'error' }))
    refreshDocuments()
  }, [])

  async function refreshDocuments() {
    try {
      const list = await fetchDocuments()
      setDocuments(list)
    } catch (error) {
      console.error(error)
    }
  }

  async function handleUpload(event) {
    event.preventDefault()
    const form = event.currentTarget
    const fileInput = form.elements.file
    if (!fileInput.files.length) {
      setDocUploadProgress('Выберите файл для загрузки.')
      return
    }
    const formData = new FormData(form)
    try {
      setDocUploadProgress('Загружаем документ...')
      await uploadDocument(formData)
      setDocUploadProgress('Документ загружен и отправлен в индексацию.')
      form.reset()
      await refreshDocuments()
    } catch (error) {
      setDocUploadProgress(error.message)
    }
  }

  async function handleChatSubmit(event) {
    event.preventDefault()
    if (!chatInput.trim()) {
      return
    }
    const draft = chatInput.trim()
    setChatInput('')
    setChatHistory((current) => [...current, { role: 'user', content: draft }])
    setIsLoading(true)
    try {
      const response = await sendChatMessage({
        user_id: userId,
        content: draft,
        metadata: { source: 'web-app' },
      })
      const reply = response.reply
      setChatHistory((current) => [...current, reply])
      setKnowledgeHits(response.knowledge_hits ?? [])
      if (reply.metadata?.plan_id) {
        setPendingPlan({
          planId: reply.metadata.plan_id,
          followups: reply.metadata.followups ?? [],
        })
      } else {
        setPendingPlan(null)
      }
    } catch (error) {
      setChatHistory((current) => [...current, { role: 'system', content: `Ошибка: ${error.message}` }])
    } finally {
      setIsLoading(false)
    }
  }

  async function handleExecutePlan() {
    if (!pendingPlan) {
      return
    }
    setIsLoading(true)
    try {
      const response = await executePlan({ plan_id: pendingPlan.planId, user_id: userId })
      setChatHistory((current) => [...current, response.reply])
      setPendingPlan(null)
    } catch (error) {
      setChatHistory((current) => [...current, { role: 'system', content: `Не удалось выполнить расчёт: ${error.message}` }])
    } finally {
      setIsLoading(false)
    }
  }

  async function handleSearch(event) {
    event.preventDefault()
    if (!searchTerm.trim()) {
      setSearchResults(null)
      return
    }
    try {
      const results = await searchKnowledge(searchTerm.trim())
      setSearchResults(results)
    } catch (error) {
      setSearchResults({ error: error.message })
    }
  }

  const knowledgeSummary = {
    totalDocuments: documents.length,
    categories: Array.from(new Set(documents.map((doc) => doc.category))).length,
  }

  return (
    <div className="app">
      <header className="app__header">
        <div>
          <h1>Alfa Pilot</h1>
          <p>Умный калькулятор с контекстом компании и учётом базы знаний.</p>
        </div>
        <div className={`status status--${healthStatus?.status ?? 'unknown'}`}>
          {healthStatus?.status === 'ok' ? 'Backend online' : 'Проверка сервиса...'}
        </div>
      </header>

      <main className="grid">
        <section className="panel">
          <h2>Память и документы</h2>
          <div className="stats">
            <div className="stat">
              <span className="stat__label">Документов</span>
              <span className="stat__value">{knowledgeSummary.totalDocuments}</span>
            </div>
            <div className="stat">
              <span className="stat__label">Категории</span>
              <span className="stat__value">{knowledgeSummary.categories}</span>
            </div>
          </div>
          <form className="upload" onSubmit={handleUpload}>
            <label className="upload__field">
              <span>Файл</span>
              <input type="file" name="file" accept=".pdf,.txt,.md,.json" required />
            </label>
            <label className="upload__field">
              <span>Название</span>
              <input type="text" name="title" placeholder="Например, финансовый отчёт" required />
            </label>
            <label className="upload__field">
              <span>Описание</span>
              <input type="text" name="description" placeholder="Краткое содержание" />
            </label>
            <label className="upload__field">
              <span>Категория</span>
              <input type="text" name="category" defaultValue="general" />
            </label>
            <label className="upload__field">
              <span>Теги</span>
              <input type="text" name="tags_json" placeholder='["финансы", "отчёт"]' />
            </label>
            <button type="submit" className="primary" disabled={isLoading}>Загрузить</button>
            {docUploadProgress && <p className="helper-text">{docUploadProgress}</p>}
          </form>
          <div className="document-list">
            <h3>Последние документы</h3>
            {documents.length === 0 ? (
              <p className="helper-text">Загрузите материалы компании, чтобы ИИ понимал контекст.</p>
            ) : (
              <ul>
                {documents.map((doc) => (
                  <li key={doc.id}>
                    <strong>{doc.title}</strong>
                    <span>{doc.category}</span>
                    <span>{new Date(doc.uploaded_at).toLocaleString()}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>

        <section className="panel">
          <h2>Диалог</h2>
          <div className="chat">
            <div className="chat__history">
              {chatHistory.map((message, index) => (
                <div key={`${message.role}-${index}`} className={`chat__message chat__message--${message.role}`}>
                  <div className="chat__role">{message.role}</div>
                  <div className="chat__content">{message.content}</div>
                </div>
              ))}
              {isLoading && <div className="chat__message chat__message--system">AI печатает...</div>}
            </div>
            <form className="chat__form" onSubmit={handleChatSubmit}>
              <textarea
                value={chatInput}
                onChange={(event) => setChatInput(event.target.value)}
                placeholder="Опишите расчёт или задайте вопрос"
                rows={3}
              />
              <button type="submit" className="primary" disabled={isLoading}>Отправить</button>
            </form>
            {pendingPlan && (
              <div className="alert">
                <strong>Нужна ваша проверка</strong>
                <p>ИИ подготовил расчёт. Подтвердите, чтобы выполнить план.</p>
                {pendingPlan.followups?.length > 0 && (
                  <ul>
                    {pendingPlan.followups.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                )}
                <button type="button" onClick={handleExecutePlan} className="primary" disabled={isLoading}>
                  Выполнить расчёт
                </button>
              </div>
            )}
          </div>
        </section>

        <section className="panel">
          <h2>Поиск по памяти</h2>
          <form className="search" onSubmit={handleSearch}>
            <input
              type="text"
              placeholder="Например: отчёт по расходам"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
            />
            <button type="submit">Искать</button>
          </form>
          {searchResults?.error && <p className="helper-text">{searchResults.error}</p>}
          {searchResults?.hits && (
            <ul className="search-results">
              {searchResults.hits.map((hit) => (
                <li key={hit.id}>
                  <strong>{(hit.metadata?.title) ?? 'Фрагмент'}</strong>
                  <p>{hit.text}</p>
                  <span>Relevance: {hit.score.toFixed(2)}</span>
                </li>
              ))}
            </ul>
          )}

          <div className="knowledge-hits">
            <h3>Контекст ответа ИИ</h3>
            {knowledgeHits.length === 0 ? (
              <p className="helper-text">Пока нет связанных фрагментов.</p>
            ) : (
              <ul>
                {knowledgeHits.map((hit) => (
                  <li key={hit.id}>
                    <strong>{(hit.metadata?.title) ?? 'Источник'}</strong>
                    <p>{hit.text}</p>
                    <span>{hit.score?.toFixed ? hit.score.toFixed(2) : hit.score}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      </main>
    </div>
  )
}

export default App
