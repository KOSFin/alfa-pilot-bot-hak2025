import { useState, useEffect } from 'react';
import { fetchDocuments, uploadDocument } from '../api';

export default function Documents({ userId, onboardingComplete }) {
  const [documents, setDocuments] = useState([]);
  const [uploadStatus, setUploadStatus] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    loadDocuments();
  }, [userId]);

  async function loadDocuments() {
    try {
      const docs = await fetchDocuments(userId);
      setDocuments(docs);
    } catch (error) {
      console.error('Failed to load documents:', error);
    }
  }

  async function handleUpload(event) {
    event.preventDefault();
    if (!onboardingComplete) {
      setUploadStatus('Завершите онбординг перед загрузкой документов');
      return;
    }

    const form = event.currentTarget;
    const fileInput = form.elements.file;
    if (!fileInput.files.length) {
      setUploadStatus('Выберите файл');
      return;
    }

    const formData = new FormData(form);
    setIsUploading(true);
    setUploadStatus('Загрузка...');

    try {
      const result = await uploadDocument(formData, userId);
      setUploadStatus(
        result.status === 'indexed'
          ? '✅ Документ загружен и проиндексирован'
          : '⚠️ Документ загружен, но индексация недоступна'
      );
      form.reset();
      await loadDocuments();
    } catch (error) {
      setUploadStatus(`❌ Ошибка: ${error.message}`);
    } finally {
      setIsUploading(false);
    }
  }

  const filteredDocs = documents.filter(
    (doc) =>
      doc.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      doc.category.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="page-container">
      <div className="card">
        <div className="card__header">
          <div>
            <h2 className="card__title">📁 Загруженные документы</h2>
            <p className="card__subtitle">
              База знаний для контекстного анализа
            </p>
          </div>
        </div>

        <div className="stats">
          <div className="stat-card">
            <div className="stat-card__value">{documents.length}</div>
            <div className="stat-card__label">Документов</div>
          </div>
          <div className="stat-card">
            <div className="stat-card__value">
              {new Set(documents.map((d) => d.category)).size}
            </div>
            <div className="stat-card__label">Категорий</div>
          </div>
        </div>

        <form onSubmit={handleUpload} style={{ marginTop: '20px' }}>
          <div className="form-field">
            <label className="form-field__label">Файл</label>
            <input
              type="file"
              name="file"
              className="form-field__input"
              accept=".pdf,.txt,.md,.json"
              required
            />
          </div>

          <div className="form-field">
            <label className="form-field__label">Название</label>
            <input
              type="text"
              name="title"
              className="form-field__input"
              placeholder="Финансовый отчёт Q4"
              required
            />
          </div>

          <div className="form-field">
            <label className="form-field__label">Описание</label>
            <input
              type="text"
              name="description"
              className="form-field__input"
              placeholder="Краткое описание содержимого"
            />
          </div>

          <div className="form-field">
            <label className="form-field__label">Категория</label>
            <input
              type="text"
              name="category"
              className="form-field__input"
              defaultValue="general"
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={isUploading || !onboardingComplete}
            style={{ width: '100%' }}
          >
            {isUploading ? 'Загрузка...' : 'Загрузить документ'}
          </button>

          {uploadStatus && (
            <p style={{ marginTop: '12px', fontSize: '14px', color: 'var(--alfa-light-gray)' }}>
              {uploadStatus}
            </p>
          )}
        </form>
      </div>

      <div className="card">
        <div className="card__header">
          <h3 className="card__title">Список документов</h3>
        </div>

        <div className="form-field">
          <input
            type="text"
            className="form-field__input"
            placeholder="🔍 Поиск по документам..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        {filteredDocs.length === 0 ? (
          <p style={{ textAlign: 'center', color: 'var(--alfa-light-gray)', padding: '20px' }}>
            {searchTerm ? 'Документы не найдены' : 'Загрузите первый документ'}
          </p>
        ) : (
          <div className="document-list">
            {filteredDocs.map((doc) => (
              <div key={doc.id} className="document-item">
                <div className="document-item__header">
                  <strong style={{ color: 'var(--alfa-white)' }}>{doc.title}</strong>
                  <span
                    style={{
                      fontSize: '12px',
                      color: doc.status === 'indexed' ? '#4ade80' : '#facc15',
                    }}
                  >
                    {doc.status === 'indexed' ? '✓ Проиндексирован' : '⏳ В обработке'}
                  </span>
                </div>
                <div style={{ fontSize: '13px', color: 'var(--alfa-light-gray)', marginTop: '4px' }}>
                  <span>📂 {doc.category}</span>
                  <span style={{ margin: '0 8px' }}>•</span>
                  <span>{new Date(doc.uploaded_at).toLocaleDateString('ru-RU')}</span>
                </div>
                {doc.description && (
                  <p style={{ fontSize: '14px', color: 'var(--alfa-light-gray)', marginTop: '8px' }}>
                    {doc.description}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
