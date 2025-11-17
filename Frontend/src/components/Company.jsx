import { useState, useEffect } from 'react';
import { fetchOnboardingState, saveCompanyProfile } from '../api';

export default function Company({ userId }) {
  const [profile, setProfile] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({
    company_name: '',
    industry: '',
    employees: '',
    annual_revenue: '',
    key_systems: '',
    goals: '',
    language: 'ru',
  });
  const [status, setStatus] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    loadProfile();
  }, [userId]);

  async function loadProfile() {
    try {
      const state = await fetchOnboardingState(userId);
      if (state.profile) {
        setProfile(state.profile);
        setFormData({
          company_name: state.profile.company_name || '',
          industry: state.profile.industry || '',
          employees: state.profile.employees != null ? String(state.profile.employees) : '',
          annual_revenue: state.profile.annual_revenue || '',
          key_systems: state.profile.key_systems || '',
          goals: state.profile.goals || '',
          language: state.profile.language || 'ru',
        });
      }
    } catch (error) {
      console.error('Failed to load profile:', error);
    }
  }

  function handleChange(e) {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setIsSaving(true);
    setStatus('Сохранение...');

    try {
      const payload = {
        user_id: userId,
        company_name: formData.company_name.trim(),
        industry: formData.industry.trim() || null,
        employees: formData.employees ? Number(formData.employees) : null,
        annual_revenue: formData.annual_revenue.trim() || null,
        key_systems: formData.key_systems.trim() || null,
        goals: formData.goals.trim() || null,
        language: formData.language || 'ru',
      };

      await saveCompanyProfile(payload);
      setStatus('✅ Профиль обновлён');
      setIsEditing(false);
      await loadProfile();
    } catch (error) {
      setStatus(`❌ Ошибка: ${error.message}`);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="page-container">
      <div className="card">
        <div className="card__header">
          <div>
            <h2 className="card__title">🏢 О компании</h2>
            <p className="card__subtitle">Профиль для персонализированного анализа</p>
          </div>
          {profile && !isEditing && (
            <button
              className="btn btn-secondary"
              onClick={() => setIsEditing(true)}
              style={{ padding: '8px 16px', fontSize: '14px' }}
            >
              ✏️ Редактировать
            </button>
          )}
        </div>

        {!profile && !isEditing ? (
          <div style={{ textAlign: 'center', padding: '40px 20px' }}>
            <p style={{ color: 'var(--alfa-light-gray)', marginBottom: '20px' }}>
              Профиль компании не заполнен
            </p>
            <button className="btn btn-primary" onClick={() => setIsEditing(true)}>
              Создать профиль
            </button>
          </div>
        ) : isEditing ? (
          <form onSubmit={handleSubmit}>
            <div className="form-field">
              <label className="form-field__label">Название компании *</label>
              <input
                type="text"
                name="company_name"
                className="form-field__input"
                value={formData.company_name}
                onChange={handleChange}
                placeholder="ООО «Альфа»"
                required
              />
            </div>

            <div className="form-field">
              <label className="form-field__label">Индустрия</label>
              <input
                type="text"
                name="industry"
                className="form-field__input"
                value={formData.industry}
                onChange={handleChange}
                placeholder="Финансы, логистика, IT..."
              />
            </div>

            <div className="form-field">
              <label className="form-field__label">Количество сотрудников</label>
              <input
                type="number"
                name="employees"
                className="form-field__input"
                value={formData.employees}
                onChange={handleChange}
                placeholder="120"
                min="0"
              />
            </div>

            <div className="form-field">
              <label className="form-field__label">Годовая выручка</label>
              <input
                type="text"
                name="annual_revenue"
                className="form-field__input"
                value={formData.annual_revenue}
                onChange={handleChange}
                placeholder="100-500 млн руб."
              />
            </div>

            <div className="form-field">
              <label className="form-field__label">Ключевые системы</label>
              <input
                type="text"
                name="key_systems"
                className="form-field__input"
                value={formData.key_systems}
                onChange={handleChange}
                placeholder="CRM, ERP, 1С"
              />
            </div>

            <div className="form-field">
              <label className="form-field__label">Цели и ожидания</label>
              <textarea
                name="goals"
                className="form-field__textarea"
                value={formData.goals}
                onChange={handleChange}
                placeholder="Автоматизация отчётности, улучшение аналитики..."
                rows={4}
              />
            </div>

            <div className="form-field">
              <label className="form-field__label">Язык транскрибации</label>
              <select
                name="language"
                className="form-field__select"
                value={formData.language}
                onChange={handleChange}
              >
                <option value="ru">Русский</option>
                <option value="en">English</option>
              </select>
            </div>

            <div style={{ display: 'flex', gap: '12px' }}>
              <button type="submit" className="btn btn-primary" disabled={isSaving} style={{ flex: 1 }}>
                {isSaving ? 'Сохранение...' : 'Сохранить'}
              </button>
              {profile && (
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => {
                    setIsEditing(false);
                    setStatus('');
                  }}
                  disabled={isSaving}
                  style={{ flex: 1 }}
                >
                  Отмена
                </button>
              )}
            </div>

            {status && (
              <p style={{ marginTop: '12px', fontSize: '14px', color: 'var(--alfa-light-gray)' }}>
                {status}
              </p>
            )}
          </form>
        ) : (
          <div className="profile-view">
            <div className="profile-field">
              <div className="profile-field__label">Компания</div>
              <div className="profile-field__value">{profile.company_name}</div>
            </div>

            {profile.industry && (
              <div className="profile-field">
                <div className="profile-field__label">Индустрия</div>
                <div className="profile-field__value">{profile.industry}</div>
              </div>
            )}

            {profile.employees && (
              <div className="profile-field">
                <div className="profile-field__label">Сотрудников</div>
                <div className="profile-field__value">{profile.employees}</div>
              </div>
            )}

            {profile.annual_revenue && (
              <div className="profile-field">
                <div className="profile-field__label">Годовая выручка</div>
                <div className="profile-field__value">{profile.annual_revenue}</div>
              </div>
            )}

            {profile.key_systems && (
              <div className="profile-field">
                <div className="profile-field__label">Ключевые системы</div>
                <div className="profile-field__value">{profile.key_systems}</div>
              </div>
            )}

            {profile.goals && (
              <div className="profile-field">
                <div className="profile-field__label">Цели и ожидания</div>
                <div className="profile-field__value">{profile.goals}</div>
              </div>
            )}

            <div className="profile-field">
              <div className="profile-field__label">Язык</div>
              <div className="profile-field__value">
                {profile.language === 'ru' ? 'Русский' : 'English'}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Company Stats Card */}
      {profile && !isEditing && (
        <div className="card">
          <h3 className="card__title">📊 Статистика использования</h3>
          <div className="stats" style={{ marginTop: '16px' }}>
            <div className="stat-card">
              <div className="stat-card__value">—</div>
              <div className="stat-card__label">Запросов</div>
            </div>
            <div className="stat-card">
              <div className="stat-card__value">—</div>
              <div className="stat-card__label">Документов</div>
            </div>
            <div className="stat-card">
              <div className="stat-card__value">—</div>
              <div className="stat-card__label">Расчётов</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
