import { useCallback, useEffect, useMemo, useState } from 'react'
import './App.css'

import {
  executePlan,
  confirmAlphaBusiness,
  fetchDocuments,
  fetchHealth,
  fetchOnboardingState,
  searchKnowledge,
  sendChatMessage,
  saveCompanyProfile,
  uploadDocument,
} from './api'

const INITIAL_CHAT_MESSAGE = 'Расскажите, какие данные или расчёты вам нужны.'
const INITIAL_COMPANY_FORM = {
  company_name: '',
  industry: '',
  employees: '',
  annual_revenue: '',
  key_systems: '',
  goals: '',
}

function usePersistentUserId() {
  return useMemo(() => {
    const tg = window.Telegram?.WebApp
    const telegramUserId = tg?.initDataUnsafe?.user?.id
    if (telegramUserId) {
      return String(telegramUserId)
    }
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
  const telegramWebApp = window.Telegram?.WebApp
  const isTelegram = Boolean(telegramWebApp)
  const appMode = useMemo(() => {
    const params = new URLSearchParams(window.location.search)
    return params.get('mode') ?? 'main'
  }, [])
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
  const [companyForm, setCompanyForm] = useState({ ...INITIAL_COMPANY_FORM })
  const [companyStatus, setCompanyStatus] = useState('')
  const [isSavingCompany, setIsSavingCompany] = useState(false)
  const [onboardingState, setOnboardingState] = useState(null)

  const loadOnboardingState = useCallback(async () => {
    try {
      const state = await fetchOnboardingState(userId)
      setOnboardingState(state)
      if (state.profile) {
        setCompanyForm({
          company_name: state.profile.company_name ?? '',
          industry: state.profile.industry ?? '',
          employees: state.profile.employees != null ? String(state.profile.employees) : '',
          annual_revenue: state.profile.annual_revenue ?? '',
          key_systems: state.profile.key_systems ?? '',
          goals: state.profile.goals ?? '',
        })
        const status = state.profile_status?.status
        if (status === 'indexed') {
          setCompanyStatus('Профиль сохранён и проиндексирован. Можно переходить к документам и диалогу.')
        } else if (status === 'processing') {
          setCompanyStatus('Профиль обрабатывается. Индексация началась, скоро всё будет готово.')
        } else if (status === 'failed') {
          setCompanyStatus('Не удалось проиндексировать профиль. Попробуйте сохранить ещё раз позже.')
        } else if (status === 'queued') {
          setCompanyStatus('Профиль сохранён и поставлен в очередь на индексацию.')
        } else {
          setCompanyStatus('Профиль сохранён. Ожидаем индексацию.')
        }
      } else {
        setCompanyForm({ ...INITIAL_COMPANY_FORM })
        setCompanyStatus('Заполните профиль, чтобы бот учитывал контекст вашей компании.')
      }
    } catch (error) {
      console.error(error)
      setOnboardingState(null)
      setCompanyForm({ ...INITIAL_COMPANY_FORM })
      setCompanyStatus('Заполните профиль, чтобы бот учитывал контекст вашей компании.')
    }
  }, [userId])

  const profileSaved = Boolean(onboardingState?.profile)
  const integrationConnected = onboardingState?.integration?.status === 'connected'
  const onboardingComplete = profileSaved && integrationConnected

  useEffect(() => {
    if (telegramWebApp) {
      telegramWebApp.ready()
      telegramWebApp.expand()
    }
    if (appMode !== 'main') {
      return
    }
    fetchHealth().then(setHealthStatus).catch(() => setHealthStatus({ status: 'error' }))
    loadOnboardingState()
    refreshDocuments()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [telegramWebApp, appMode, loadOnboardingState])

  async function refreshDocuments() {
    try {
      const list = await fetchDocuments()
      setDocuments(list)
    } catch (error) {
      console.error(error)
    }
  }

  function handleCompanyFieldChange(event) {
    const { name, value } = event.target
    setCompanyForm((current) => ({ ...current, [name]: value }))
  }

  async function handleCompanySubmit(event) {
    event.preventDefault()
    if (!companyForm.company_name.trim()) {
      setCompanyStatus('Введите название компании.')
      return
    }

    const payload = {
      user_id: userId,
      company_name: companyForm.company_name.trim(),
      industry: companyForm.industry.trim() || null,
      employees: companyForm.employees ? Number(companyForm.employees) : null,
      annual_revenue: companyForm.annual_revenue.trim() || null,
      key_systems: companyForm.key_systems.trim() || null,
      goals: companyForm.goals.trim() || null,
    }

    setCompanyStatus('Сохраняем профиль...')
    setIsSavingCompany(true)
    try {
      await saveCompanyProfile(payload)
      setCompanyStatus('Профиль сохранён! Уведомление отправлено в бот.')
      
      if (isTelegram) {
        telegramWebApp?.sendData(JSON.stringify({ type: 'company_profile', user_id: userId }))
        setTimeout(() => {
          telegramWebApp?.close()
        }, 1500)
      } else {
        await loadOnboardingState()
      }
    } catch (error) {
      setCompanyStatus(error.message)
    } finally {
      setIsSavingCompany(false)
    }
  }

  async function handleUpload(event) {
    event.preventDefault()
    if (!onboardingComplete) {
      setDocUploadProgress('Сначала завершите онбординг, чтобы загружать документы.')
      return
    }
    const form = event.currentTarget
    const fileInput = form.elements.file
    if (!fileInput.files.length) {
      setDocUploadProgress('Выберите файл для загрузки.')
      return
    }
    const formData = new FormData(form)
    try {
      setDocUploadProgress('Загружаем документ...')
      const uploaded = await uploadDocument(formData)
      if (uploaded.status === 'indexed') {
        setDocUploadProgress('Документ загружен и отправлен в индексацию.')
      } else {
        setDocUploadProgress('Документ сохранён, но эмбеддинг недоступен. Попробуйте позже.')
      }
      form.reset()
      await refreshDocuments()
    } catch (error) {
      setDocUploadProgress(error.message)
    }
  }

  async function handleChatSubmit(event) {
    event.preventDefault()
    if (!onboardingComplete) {
      return
    }
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

  if (appMode === 'integration') {
    return (
      <IntegrationStub
        userId={userId}
        telegramWebApp={telegramWebApp}
        isTelegram={isTelegram}
      />
    )
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
          <h2>Профиль компании</h2>
          <p>
            Заполните краткую анкету, чтобы ИИ учитывал контекст вашего бизнеса. В Telegram мини-приложение
            автоматически закроется после сохранения.
          </p>
          <form className="upload" onSubmit={handleCompanySubmit}>
            <label className="upload__field">
              <span>Название компании</span>
              <input
                type="text"
                name="company_name"
                placeholder="Например, ООО «Альфа»"
                value={companyForm.company_name}
                onChange={handleCompanyFieldChange}
                required
              />
            </label>
            <label className="upload__field">
              <span>Индустрия</span>
              <input
                type="text"
                name="industry"
                placeholder="Финансы, логистика, IT..."
                value={companyForm.industry}
                onChange={handleCompanyFieldChange}
              />
            </label>
            <label className="upload__field">
              <span>Количество сотрудников</span>
              <input
                type="number"
                min="0"
                name="employees"
                placeholder="Например, 120"
                value={companyForm.employees}
                onChange={handleCompanyFieldChange}
              />
            </label>
            <label className="upload__field">
              <span>Годовая выручка</span>
              <input
                type="text"
                name="annual_revenue"
                placeholder="Диапазон или оценка"
                value={companyForm.annual_revenue}
                onChange={handleCompanyFieldChange}
              />
            </label>
            <label className="upload__field">
              <span>Ключевые системы и сервисы</span>
              <input
                type="text"
                name="key_systems"
                placeholder="CRM, ERP, учётные системы"
                value={companyForm.key_systems}
                onChange={handleCompanyFieldChange}
              />
            </label>
            <label className="upload__field">
              <span>Цели и ожидания</span>
              <textarea
                name="goals"
                rows={3}
                placeholder="Опишите, что важно автоматизировать"
                value={companyForm.goals}
                onChange={handleCompanyFieldChange}
              />
            </label>
            <button type="submit" className="primary" disabled={isSavingCompany}>
              Сохранить профиль
            </button>
            {companyStatus && <p className="helper-text">{companyStatus}</p>}
            {isTelegram && (
              <p className="helper-text">После сохранения бот отправит подтверждение, окно можно закрыть вручную.</p>
            )}
          </form>
          {profileSaved && !integrationConnected && (
            <p className="helper-text">Профиль сохранён. Следующий шаг — подключите Альфа-Бизнес через команду /start в Telegram.</p>
          )}
          {integrationConnected && (
            <p className="helper-text">Альфа-Бизнес подключён. Можно продолжать работу с документами и диалогом.</p>
          )}
        </section>

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
            <button type="submit" className="primary" disabled={isLoading || !onboardingComplete}>Загрузить</button>
            {docUploadProgress && <p className="helper-text">{docUploadProgress}</p>}
            {!onboardingComplete && (
              <p className="helper-text">Заполнение профиля и подключение Альфа-Бизнес обязательны перед загрузкой документов.</p>
            )}
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
                    <span>Статус: {doc.status === 'indexed' ? 'проиндексирован' : 'эмбеддинг недоступен'}</span>
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
                disabled={!onboardingComplete}
              />
              <button type="submit" className="primary" disabled={isLoading || !onboardingComplete}>Отправить</button>
            </form>
            {!onboardingComplete && (
              <p className="helper-text">Сначала завершите заполнение профиля и подключение Альфа-Бизнес, затем продолжайте диалог.</p>
            )}
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

function IntegrationStub({ userId, telegramWebApp, isTelegram }) {
  const [status, setStatus] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (telegramWebApp) {
      telegramWebApp.ready()
      telegramWebApp.expand()
    }
  }, [telegramWebApp])

  async function handleConnect() {
    setIsSubmitting(true)
    try {
      await confirmAlphaBusiness({ user_id: userId })
      setStatus('Интеграция подключена! Уведомление отправлено в бот.')
      if (telegramWebApp) {
        telegramWebApp.sendData(JSON.stringify({ type: 'alpha_business_connected', user_id: userId }))
        setTimeout(() => telegramWebApp.close(), 1500)
      }
    } catch (error) {
      setStatus(error.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="integration-screen">
      <header className="integration-screen__header">
        <h1>Alfa Pilot</h1>
        <p>Подключение Альфа-Бизнес</p>
      </header>
      <main className="integration-screen__body">
        <p>
          Подключение нужно, чтобы ассистент видел операции и мог точнее подсказывать. Нажмите кнопку ниже, и мы
          отметим интеграцию.
        </p>
        <button type="button" className="primary" onClick={handleConnect} disabled={isSubmitting}>
          {isSubmitting ? 'Подключаем...' : 'Подключить'}
        </button>
        {status && <p className="helper-text">{status}</p>}
        {!isTelegram && <p className="helper-text">Эта страница рассчитана на запуск из Telegram мини-приложения.</p>}
      </main>
    </div>
  )
}

export default App
