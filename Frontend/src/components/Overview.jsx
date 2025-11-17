import { useState, useEffect } from 'react';
import { fetchOnboardingState } from '../api';

export default function Overview({ userId }) {
  const [integrationData, setIntegrationData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadOverviewData();
  }, [userId]);

  async function loadOverviewData() {
    try {
      const state = await fetchOnboardingState(userId);
      setIntegrationData(state.integration);
    } catch (error) {
      console.error('Failed to load overview:', error);
    } finally {
      setLoading(false);
    }
  }

  const mockAccountData = {
    balance: '2 456 789.50',
    currency: '₽',
    accountNumber: '•••• 4521',
    recentTransactions: [
      { id: 1, name: 'Поступление от клиента', amount: '+125 000', date: '17.11.2024' },
      { id: 2, name: 'Аренда офиса', amount: '−85 000', date: '15.11.2024' },
      { id: 3, name: 'Зарплата сотрудникам', amount: '−450 000', date: '10.11.2024' },
      { id: 4, name: 'Поставка товаров', amount: '−120 000', date: '08.11.2024' },
    ],
  };

  return (
    <div className="page-container">
      <div className="card balance-card">
        <div className="balance-card__header">
          <div>
            <div className="balance-card__label">Основной счёт</div>
            <div className="balance-card__number">{mockAccountData.accountNumber}</div>
          </div>
          <div className="balance-card__status">
            {integrationData?.status === 'connected' ? (
              <span style={{ color: '#4ade80' }}>✓ Подключено</span>
            ) : (
              <span style={{ color: '#facc15' }}>⚠ Не подключено</span>
            )}
          </div>
        </div>
        <div className="balance-card__amount">
          <span className="balance-card__amount-value">{mockAccountData.balance}</span>
          <span className="balance-card__amount-currency">{mockAccountData.currency}</span>
        </div>
        <div className="balance-card__footer">
          <button className="btn btn-primary" style={{ flex: 1 }}>
            Пополнить
          </button>
          <button className="btn btn-secondary" style={{ flex: 1 }}>
            Перевести
          </button>
        </div>
      </div>

      <div className="card">
        <h3 className="card__title">📊 Статистика за месяц</h3>
        <div className="stats" style={{ marginTop: '16px' }}>
          <div className="stat-card">
            <div className="stat-card__value" style={{ color: '#4ade80' }}>
              +2.4M
            </div>
            <div className="stat-card__label">Доход</div>
          </div>
          <div className="stat-card">
            <div className="stat-card__value" style={{ color: 'var(--alfa-red)' }}>
              −1.8M
            </div>
            <div className="stat-card__label">Расход</div>
          </div>
          <div className="stat-card">
            <div className="stat-card__value">+600K</div>
            <div className="stat-card__label">Прибыль</div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card__header">
          <h3 className="card__title">💳 Последние операции</h3>
          <button className="btn btn-secondary" style={{ padding: '8px 16px', fontSize: '14px' }}>
            Все операции
          </button>
        </div>

        <div className="transactions-list">
          {mockAccountData.recentTransactions.map((tx) => (
            <div key={tx.id} className="transaction-item">
              <div className="transaction-item__icon">
                {tx.amount.startsWith('+') ? '📥' : '📤'}
              </div>
              <div className="transaction-item__info">
                <div className="transaction-item__name">{tx.name}</div>
                <div className="transaction-item__date">{tx.date}</div>
              </div>
              <div
                className="transaction-item__amount"
                style={{ color: tx.amount.startsWith('+') ? '#4ade80' : 'var(--alfa-white)' }}
              >
                {tx.amount} ₽
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <h3 className="card__title">🤖 Активность AI-ассистента</h3>
        <div className="ai-stats">
          <div className="ai-stat-item">
            <div className="ai-stat-item__icon">💬</div>
            <div className="ai-stat-item__info">
              <div className="ai-stat-item__value">24</div>
              <div className="ai-stat-item__label">Диалога</div>
            </div>
          </div>
          <div className="ai-stat-item">
            <div className="ai-stat-item__icon">🧮</div>
            <div className="ai-stat-item__info">
              <div className="ai-stat-item__value">12</div>
              <div className="ai-stat-item__label">Расчётов</div>
            </div>
          </div>
          <div className="ai-stat-item">
            <div className="ai-stat-item__icon">📄</div>
            <div className="ai-stat-item__info">
              <div className="ai-stat-item__value">8</div>
              <div className="ai-stat-item__label">Документов</div>
            </div>
          </div>
        </div>
      </div>

      {integrationData?.status !== 'connected' && (
        <div className="card" style={{ background: 'var(--alfa-red)', borderColor: 'var(--alfa-red)' }}>
          <h3 className="card__title" style={{ color: 'var(--alfa-white)' }}>
            ⚠️ Подключите Альфа-Бизнес
          </h3>
          <p style={{ color: 'var(--alfa-white)', marginTop: '8px' }}>
            Для просмотра реальных данных счёта подключите интеграцию с Альфа-Бизнес
          </p>
          <button className="btn" style={{ marginTop: '16px', background: 'var(--alfa-white)', color: 'var(--alfa-red)' }}>
            Подключить сейчас
          </button>
        </div>
      )}
    </div>
  );
}
