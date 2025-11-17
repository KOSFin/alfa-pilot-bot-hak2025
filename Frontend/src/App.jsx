import { useCallback, useEffect, useMemo, useState } from 'react';
import './App.css';

import Documents from './components/Documents';
import Company from './components/Company';
import Search from './components/Search';
import Overview from './components/Overview';
import Calculator from './components/Calculator';

import { fetchOnboardingState, confirmAlphaBusiness } from './api';

function usePersistentUserId() {
  return useMemo(() => {
    const storageKey = 'alfa-pilot-user-id';
    const params = new URLSearchParams(window.location.search);
    const userIdFromQuery = params.get('tg_user_id') || params.get('user_id');
    if (userIdFromQuery) {
      window.localStorage.setItem(storageKey, userIdFromQuery);
      return userIdFromQuery;
    }
    const tg = window.Telegram?.WebApp;
    const telegramUserId = tg?.initDataUnsafe?.user?.id;
    if (telegramUserId) {
      return String(telegramUserId);
    }
    const stored = window.localStorage.getItem(storageKey);
    if (stored) {
      return stored;
    }
    const uuid =
      window.crypto && typeof window.crypto.randomUUID === 'function'
        ? window.crypto.randomUUID()
        : Math.random().toString(36).slice(2);
    window.localStorage.setItem(storageKey, uuid);
    return uuid;
  }, []);
}

function App() {
  const userId = usePersistentUserId();
  const telegramWebApp = window.Telegram?.WebApp;
  const isTelegram = Boolean(telegramWebApp);

  const [currentTab, setCurrentTab] = useState('overview');
  const [onboardingState, setOnboardingState] = useState(null);

  useEffect(() => {
    if (telegramWebApp) {
      telegramWebApp.ready();
      telegramWebApp.expand();
    }
    loadOnboardingState();
  }, [telegramWebApp]);

  async function loadOnboardingState() {
    try {
      const state = await fetchOnboardingState(userId);
      setOnboardingState(state);
    } catch (error) {
      console.error('Failed to load onboarding state:', error);
      setOnboardingState(null);
    }
  }


  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const mode = params.get('mode');
    const calcData = params.get('calc_data');

    if (mode === 'integration') {
      setCurrentTab('integration');
    } else if (calcData) {
      setCurrentTab('calculator');
    }
  }, []);

  const profileSaved = Boolean(onboardingState?.profile);
  const integrationConnected = onboardingState?.integration?.status === 'connected';
  const onboardingComplete = profileSaved && integrationConnected;


  if (currentTab === 'integration') {
    return (
      <IntegrationView
        userId={userId}
        telegramWebApp={telegramWebApp}
        onComplete={() => {
          loadOnboardingState();
          setCurrentTab('overview');
        }}
      />
    );
  }


  return (
    <div className="app-container">
      <header className="app-header">
        <div className="app-header__logo">
          <div className="app-header__logo-icon">А</div>
          <span>Alfa Pilot</span>
        </div>
        <div className="app-header__status">
          {onboardingComplete ? '✓ Готов к работе' : '⚠ Завершите настройку'}
        </div>
      </header>

      <main className="app-main">
        {currentTab === 'overview' && <Overview userId={userId} />}
        {currentTab === 'documents' && (
          <Documents userId={userId} onboardingComplete={onboardingComplete} />
        )}
        {currentTab === 'company' && <Company userId={userId} />}
        {currentTab === 'search' && <Search userId={userId} />}
        {currentTab === 'calculator' && <Calculator userId={userId} />}
      </main>

      <nav className="bottom-nav">
        <button
          className={`bottom-nav__item ${currentTab === 'overview' ? 'bottom-nav__item--active' : ''}`}
          onClick={() => setCurrentTab('overview')}
        >
          <span className="bottom-nav__icon">📊</span>
          <span>Обзор</span>
        </button>
        <button
          className={`bottom-nav__item ${currentTab === 'documents' ? 'bottom-nav__item--active' : ''}`}
          onClick={() => setCurrentTab('documents')}
        >
          <span className="bottom-nav__icon">📁</span>
          <span>Документы</span>
        </button>
        <button
          className={`bottom-nav__item ${currentTab === 'calculator' ? 'bottom-nav__item--active' : ''}`}
          onClick={() => setCurrentTab('calculator')}
        >
          <span className="bottom-nav__icon">🧮</span>
          <span>Калькулятор</span>
        </button>
        <button
          className={`bottom-nav__item ${currentTab === 'search' ? 'bottom-nav__item--active' : ''}`}
          onClick={() => setCurrentTab('search')}
        >
          <span className="bottom-nav__icon">🔍</span>
          <span>Поиск</span>
        </button>
        <button
          className={`bottom-nav__item ${currentTab === 'company' ? 'bottom-nav__item--active' : ''}`}
          onClick={() => setCurrentTab('company')}
        >
          <span className="bottom-nav__icon">🏢</span>
          <span>Компания</span>
        </button>
      </nav>
    </div>
  );
}

function IntegrationView({ userId, telegramWebApp, onComplete }) {
  const [status, setStatus] = useState('');
  const [isConnecting, setIsConnecting] = useState(false);

  async function handleConnect() {
    setIsConnecting(true);
    setStatus('Подключение...');
    try {
      await confirmAlphaBusiness({ user_id: userId });
      setStatus('✅ Интеграция подключена!');

      if (telegramWebApp) {
        telegramWebApp.sendData(
          JSON.stringify({ type: 'alpha_business_connected', user_id: userId })
        );
        setTimeout(() => telegramWebApp.close(), 1500);
      } else {
        setTimeout(() => onComplete(), 1500);
      }
    } catch (error) {
      setStatus(`❌ Ошибка: ${error.message}`);
    } finally {
      setIsConnecting(false);
    }
  }

  return (
    <div className="integration-screen">
      <header className="integration-screen__header">
        <h1>🔗 Alfa Pilot</h1>
        <p>Подключение Альфа-Бизнес</p>
      </header>
      <main className="integration-screen__body">
        <div className="card">
          <p style={{ fontSize: '16px', marginBottom: '12px' }}>
            <strong>Последний шаг!</strong>
          </p>
          <p style={{ color: 'var(--alfa-light-gray)', marginBottom: '20px' }}>
            Подключите Альфа-Бизнес для получения реальных данных о счёте и транзакциях.
          </p>
          <button
            className="btn btn-primary"
            onClick={handleConnect}
            disabled={isConnecting}
            style={{ width: '100%', marginBottom: '12px' }}
          >
            {isConnecting ? 'Подключаем...' : 'Подключить Альфа-Бизнес'}
          </button>
          <button
            className="btn btn-secondary"
            onClick={() => onComplete()}
            disabled={isConnecting}
            style={{ width: '100%' }}
          >
            Пропустить
          </button>
          {status && (
            <p style={{ marginTop: '12px', fontSize: '14px', textAlign: 'center' }}>
              {status}
            </p>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
