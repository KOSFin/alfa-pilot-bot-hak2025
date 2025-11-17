import { useState } from 'react';
import { searchKnowledge } from '../api';

export default function Search({ userId }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedFilter, setSelectedFilter] = useState('all');

  async function handleSearch(e) {
    e.preventDefault();
    if (!searchTerm.trim()) return;

    setIsSearching(true);
    try {
      const results = await searchKnowledge(searchTerm.trim());
      setSearchResults(results);
    } catch (error) {
      setSearchResults({ error: error.message });
    } finally {
      setIsSearching(false);
    }
  }

  const filters = [
    { id: 'all', label: 'Всё', icon: '🔍' },
    { id: 'documents', label: 'Документы', icon: '📄' },
    { id: 'chats', label: 'Диалоги', icon: '💬' },
    { id: 'calculations', label: 'Расчёты', icon: '🧮' },
  ];

  return (
    <div className="page-container">
      <div className="card">
        <div className="card__header">
          <div>
            <h2 className="card__title">🔍 Поиск по базе знаний</h2>
            <p className="card__subtitle">Найдите информацию во всех документах и диалогах</p>
          </div>
        </div>

        <form onSubmit={handleSearch}>
          <div className="search-container">
            <input
              type="text"
              className="search-input"
              placeholder="Поиск по документам, чатам, расчётам..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            <button type="submit" className="btn btn-primary" disabled={isSearching}>
              {isSearching ? '⏳' : '🔍'}
            </button>
          </div>
        </form>

        {/* Filters */}
        <div className="filter-chips">
          {filters.map((filter) => (
            <button
              key={filter.id}
              className={`filter-chip ${selectedFilter === filter.id ? 'filter-chip--active' : ''}`}
              onClick={() => setSelectedFilter(filter.id)}
            >
              <span>{filter.icon}</span>
              <span>{filter.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Search Results */}
      {searchResults && (
        <div className="card">
          <h3 className="card__title">Результаты поиска</h3>

          {searchResults.error ? (
            <p style={{ color: 'var(--alfa-red)', textAlign: 'center', padding: '20px' }}>
              Ошибка: {searchResults.error}
            </p>
          ) : searchResults.hits && searchResults.hits.length > 0 ? (
            <div className="search-results">
              {searchResults.hits.map((hit) => (
                <div key={hit.id} className="search-result-item">
                  <div className="search-result-item__header">
                    <span className="search-result-item__title">
                      {hit.metadata?.title || 'Фрагмент из базы знаний'}
                    </span>
                    <span className="search-result-item__score">
                      {(hit.score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <p className="search-result-item__text">{hit.text}</p>
                  {hit.metadata?.category && (
                    <span className="search-result-item__tag">📂 {hit.metadata.category}</span>
                  )}
                </div>
              ))}
            </div>
          ) : searchResults.hits ? (
            <p style={{ textAlign: 'center', color: 'var(--alfa-light-gray)', padding: '40px 20px' }}>
              Ничего не найдено. Попробуйте другой запрос
            </p>
          ) : null}
        </div>
      )}

      {/* Search Tips */}
      {!searchResults && (
        <div className="card">
          <h3 className="card__title">💡 Советы по поиску</h3>
          <ul className="tips-list">
            <li>Используйте ключевые слова из ваших документов</li>
            <li>Поиск работает по содержимому документов и истории диалогов</li>
            <li>Чем конкретнее запрос, тем точнее результаты</li>
            <li>Поддерживаются русский и английский языки</li>
          </ul>
        </div>
      )}
    </div>
  );
}
