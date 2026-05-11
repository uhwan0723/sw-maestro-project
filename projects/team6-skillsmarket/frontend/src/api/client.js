// fetch 래퍼. 3개 엔드포인트만 노출한다.
//
// BE 실제 명세 (architect contract v2 — 2026-05-09 정렬):
//   GET /skills?category=...        → { skills: [{ id, title, description }] }
//   GET /skills/{id}                → { id, title, description, category, content }
//   GET /skills/recommendation?...  → { skills: [{ id, title, description, percentage }] }
//
// 에러 응답: Spring 기본 형태 ({ timestamp, status, error, message, path }).
// FE 는 `payload.code` fallback 으로 'UNKNOWN' 처리.

import { API_BASE } from '../config.js';

export class ApiError extends Error {
  constructor(status, code, message) {
    super(message || code || `HTTP ${status}`);
    this.name = 'ApiError';
    this.status = status;
    this.code = code || 'UNKNOWN';
  }
}

export class NetworkError extends Error {
  constructor(cause) {
    super('백엔드 서버에 연결할 수 없습니다.');
    this.name = 'NetworkError';
    this.cause = cause;
  }
}

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method: options.method || 'GET',
      headers: {
        Accept: 'application/json',
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      },
      ...(options.body ? { body: JSON.stringify(options.body) } : {}),
    });
  } catch (err) {
    // CORS / DNS / connection refused 등은 fetch 자체에서 throw.
    throw new NetworkError(err);
  }

  if (!res.ok) {
    let payload = {};
    try {
      payload = await res.json();
    } catch {
      // body 가 비어 있거나 JSON 이 아닌 경우 무시.
    }
    throw new ApiError(
      res.status,
      payload.code || 'UNKNOWN',
      payload.message || res.statusText
    );
  }

  return res.json();
}

// BE 는 category 를 필수로 요구한다 (@RequestParam SkillCategory category).
// All 칩은 FE 에서 제거됨. enum 은 모두 UPPER_SNAKE.
export function getSkills(category) {
  return request(`/skills?category=${encodeURIComponent(category)}`);
}

export function getSkill(id) {
  return request(`/skills/${encodeURIComponent(id)}`);
}

// BE 경로는 단수 `/recommendation`. topK 는 BE 기본값 3 사용 (미전송).
export function recommend(query) {
  return request(`/skills/recommendation?query=${encodeURIComponent(query)}`);
}

// POST /skills/generate → 202 { requestId, status }
export function generateSkill(userPrompt) {
  return request('/skills/generate', {
    method: 'POST',
    body: { userPrompt },
  });
}

// GET /skills/generate/{requestId} → { requestId, status, finalSkillContent? }
export function getGenerationStatus(requestId) {
  return request(`/skills/generate/${encodeURIComponent(requestId)}`);
}
