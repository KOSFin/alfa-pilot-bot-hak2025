import { useState, useEffect } from 'react';
import { sendChatMessage, executePlan } from '../api';

export default function Calculator({ userId }) {
  const [input, setInput] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [pendingPlan, setPendingPlan] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [usedTools, setUsedTools] = useState([]);


  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const calcData = params.get('calc_data');
    if (calcData) {
      try {
        const data = JSON.parse(decodeURIComponent(calcData));
        if (data.question) {
          setInput(data.question);
        }
      } catch (error) {
        console.error('Failed to parse calculator data:', error);
      }
    }
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!input.trim() || isProcessing) return;

    const userMessage = input.trim();
    setInput('');
    setChatHistory((prev) => [...prev, { role: 'user', content: userMessage }]);
    setIsProcessing(true);

    try {
      const response = await sendChatMessage({
        user_id: userId,
        content: userMessage,
        metadata: { source: 'calculator' },
      });

      setChatHistory((prev) => [...prev, response.reply]);


      if (response.reply.metadata?.tools_used) {
        setUsedTools(response.reply.metadata.tools_used);
      }

      if (response.reply.metadata?.plan_id) {
        setPendingPlan({
          planId: response.reply.metadata.plan_id,
          followups: response.reply.metadata.followups || [],
        });
      } else {
        setPendingPlan(null);
      }
    } catch (error) {
      setChatHistory((prev) => [
        ...prev,
        { role: 'system', content: `Ошибка: ${error.message}` },
      ]);
    } finally {
      setIsProcessing(false);
    }
  }

  async function handleExecutePlan() {
    if (!pendingPlan) return;

    setIsProcessing(true);
    try {
      const response = await executePlan({
        plan_id: pendingPlan.planId,
        user_id: userId,
      });

      setChatHistory((prev) => [...prev, response.reply]);

      if (response.reply.metadata?.tools_used) {
        setUsedTools(response.reply.metadata.tools_used);
      }

      setPendingPlan(null);
    } catch (error) {
      setChatHistory((prev) => [
        ...prev,
        { role: 'system', content: `Ошибка выполнения: ${error.message}` },
      ]);
    } finally {
      setIsProcessing(false);
    }
  }

  function shareCalculation() {
    const lastCalc = chatHistory[chatHistory.length - 1];
    if (!lastCalc) return;

    const calcData = {
      question: chatHistory.find((m) => m.role === 'user')?.content || '',
      result: lastCalc.content,
      timestamp: new Date().toISOString(),
    };

    const encoded = encodeURIComponent(JSON.stringify(calcData));
    const shareUrl = `https://t.me/aalfa_bot?startapp=${encoded}`;

    navigator.clipboard.writeText(shareUrl).then(() => {
      alert('Ссылка скопирована! Отправьте её через бота.');
    });
  }

  return (
    <div className="page-container calculator-page">
      <div className="card">
        <div className="card__header">
          <div>
            <h2 className="card__title">🧮 Калькулятор</h2>
            <p className="card__subtitle">AI-расчёты с контекстом вашей компании</p>
          </div>
        </div>

        <div className="calculator-chat">
          {chatHistory.length === 0 ? (
            <div className="calculator-empty">
              <div style={{ fontSize: '48px', marginBottom: '16px' }}>🧮</div>
              <p style={{ color: 'var(--alfa-light-gray)' }}>
                Задайте вопрос для расчёта или анализа
              </p>
              <div className="quick-actions">
                <button
                  className="quick-action-btn"
                  onClick={() => setInput('Рассчитай прогноз выручки на следующий квартал')}
                >
                  📈 Прогноз выручки
                </button>
                <button
                  className="quick-action-btn"
                  onClick={() => setInput('Посчитай ROI для нового проекта')}
                >
                  💰 Расчёт ROI
                </button>
                <button
                  className="quick-action-btn"
                  onClick={() => setInput('Анализ структуры расходов')}
                >
                  📊 Анализ расходов
                </button>
              </div>
            </div>
          ) : (
            <div className="calculator-messages">
              {chatHistory.map((msg, idx) => (
                <div key={idx} className={`calc-message calc-message--${msg.role}`}>
                  <div className="calc-message__avatar">
                    {msg.role === 'user' ? '👤' : msg.role === 'assistant' ? '🤖' : 'ℹ️'}
                  </div>
                  <div className="calc-message__content">
                    <div className="calc-message__text">{msg.content}</div>
                    {msg.metadata?.calculation_result && (
                      <div className="calc-result-box">
                        <div className="calc-result-box__title">📊 Результат расчёта:</div>
                        <div className="calc-result-box__value">
                          {msg.metadata.calculation_result}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {isProcessing && (
                <div className="calc-message calc-message--assistant">
                  <div className="calc-message__avatar">🤖</div>
                  <div className="calc-message__content">
                    <div className="typing-indicator">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {pendingPlan && (
            <div className="plan-confirmation">
              <div className="plan-confirmation__header">
                <strong>✅ План расчёта подготовлен</strong>
              </div>
              <p>AI подготовил план действий. Подтвердите выполнение:</p>
              {pendingPlan.followups?.length > 0 && (
                <ul className="plan-confirmation__steps">
                  {pendingPlan.followups.map((step, idx) => (
                    <li key={idx}>{step}</li>
                  ))}
                </ul>
              )}
              <button
                className="btn btn-primary"
                onClick={handleExecutePlan}
                disabled={isProcessing}
                style={{ width: '100%' }}
              >
                Выполнить расчёт
              </button>
            </div>
          )}

          {usedTools.length > 0 && (
            <div className="used-tools">
              <div className="used-tools__title">🛠 Использованные инструменты:</div>
              <div className="used-tools__list">
                {usedTools.map((tool, idx) => (
                  <span key={idx} className="tool-badge">
                    {tool.icon || '🔧'} {tool.name}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit} className="calculator-input">
          <textarea
            className="calculator-input__field"
            placeholder="Опишите задачу для расчёта..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            rows={3}
            disabled={isProcessing}
          />
          <div className="calculator-input__actions">
            {chatHistory.length > 0 && (
              <button
                type="button"
                className="btn btn-secondary"
                onClick={shareCalculation}
                style={{ flex: 1 }}
              >
                📤 Поделиться
              </button>
            )}
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isProcessing || !input.trim()}
              style={{ flex: 2 }}
            >
              {isProcessing ? 'Обработка...' : 'Рассчитать'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
