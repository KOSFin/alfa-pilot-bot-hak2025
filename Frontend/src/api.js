const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api';

const defaultHeaders = {
  'Content-Type': 'application/json',
};

export async function fetchDocuments() {
  const response = await fetch(`${API_BASE_URL}/knowledge/documents`);
  if (!response.ok) {
    throw new Error('Не удалось загрузить документы');
  }
  return response.json();
}

export async function uploadDocument(formData) {
  const response = await fetch(`${API_BASE_URL}/knowledge/documents`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail ?? 'Ошибка при загрузке документа');
  }
  return response.json();
}

export async function searchKnowledge(query) {
  const response = await fetch(`${API_BASE_URL}/knowledge/search?query=${encodeURIComponent(query)}`);
  if (!response.ok) {
    throw new Error('Ошибка поиска');
  }
  return response.json();
}

export async function sendChatMessage(payload) {
  const response = await fetch(`${API_BASE_URL}/chat/messages`, {
    method: 'POST',
    headers: defaultHeaders,
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || 'Ошибка при отправке сообщения');
  }
  return response.json();
}

export async function saveCompanyProfile(payload) {
  const response = await fetch(`${API_BASE_URL}/integration/profile`, {
    method: 'POST',
    headers: defaultHeaders,
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail ?? 'Не удалось сохранить профиль компании');
  }
  return response.json();
}

export async function confirmAlphaBusiness(payload) {
  const response = await fetch(`${API_BASE_URL}/integration/alpha-business`, {
    method: 'POST',
    headers: defaultHeaders,
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail ?? 'Не удалось подтвердить интеграцию');
  }
  return response.json();
}

export async function executePlan(payload) {
  const response = await fetch(`${API_BASE_URL}/chat/execute`, {
    method: 'POST',
    headers: defaultHeaders,
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error('Ошибка выполнения расчёта');
  }
  return response.json();
}

export async function fetchHealth() {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error('Сервис недоступен');
  }
  return response.json();
}

export function getApiBaseUrl() {
  return API_BASE_URL;
}
