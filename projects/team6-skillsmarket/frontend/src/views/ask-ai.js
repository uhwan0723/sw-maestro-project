// Ask AI 뷰: 자연어 의도 입력 → RAG 추천 결과.
//
// 응답 shape (architect contract §3.4):
//   { skills: [{ id, title, description, percentage }, ...] }
// percentage 는 0~100 정수. 50 이하는 백엔드가 이미 제외(51 이상만 반환).
// 따라서 빈 배열일 때만 "결과 없음" 안내를 띄우면 된다.

import { recommend, ApiError, NetworkError } from '../api/client.js';
import { escapeHtml, $, $$, showNetBanner } from '../lib/ui.js';
import { openSkillDetail } from './skill-detail.js';

function renderMatch(match) {
  const score = Math.max(0, Math.min(100, Number(match.percentage) || 0));
  return `
    <div class="intent-match" data-id="${escapeHtml(match.id)}" tabindex="0" role="button" aria-label="${escapeHtml(match.title)} 상세 보기">
      <div>
        <div class="intent-match-name">${escapeHtml(match.title)}</div>
        <div class="intent-match-reason">${escapeHtml(match.description)}</div>
      </div>
      <div class="intent-score">
        <span>match ${score}%</span>
        <div class="score-bar"><div class="score-fill" style="width:${score}%"></div></div>
      </div>
    </div>
  `;
}

function renderResults(query, skills) {
  const r = $('#intent-results');
  if (!r) return;

  const queryLine = `<div class="intent-q">QUERY → <span>"${escapeHtml(query)}"</span></div>`;
  const hasResults = Array.isArray(skills) && skills.length > 0;

  if (!hasResults) {
    r.innerHTML =
      queryLine +
      '<div class="intent-empty">매칭 점수 50% 이상의 스킬을 찾지 못했습니다. 쿼리를 다시 적어보세요.</div>';
  } else {
    r.innerHTML = queryLine + skills.map(renderMatch).join('');
  }
  r.classList.add('show');

  // hero stats: 마지막 매칭 점수 (= 결과 배열의 마지막 항목, 없으면 '—').
  const stat = document.getElementById('stat-accuracy');
  if (stat) {
    if (hasResults) {
      const last = skills[skills.length - 1];
      const pct = Math.max(0, Math.min(100, Number(last.percentage) || 0));
      stat.textContent = `${pct}%`;
    } else {
      stat.textContent = '—';
    }
  }
}

function renderError(query, message) {
  const r = $('#intent-results');
  if (!r) return;
  const queryLine = `<div class="intent-q">QUERY → <span>"${escapeHtml(query)}"</span></div>`;
  r.innerHTML =
    queryLine +
    `<div class="intent-empty" style="color:var(--warn);border-color:rgba(255,107,61,.35)">${escapeHtml(message)}</div>`;
  r.classList.add('show');
}

async function runQuery(query) {
  const trimmed = (query || '').trim();
  const input = $('#intent-input');
  if (!trimmed) {
    if (input) {
      input.focus();
      input.classList.remove('shake');
      // 강제 reflow 로 애니메이션 재시작
      void input.offsetWidth;
      input.classList.add('shake');
    }
    return;
  }

  // 즉시 로딩 상태
  const r = $('#intent-results');
  if (r) {
    r.innerHTML =
      `<div class="intent-q">QUERY → <span>"${escapeHtml(trimmed)}"</span></div>` +
      '<div class="intent-empty">매칭 중...</div>';
    r.classList.add('show');
  }

  try {
    const data = await recommend(trimmed);
    renderResults(trimmed, data.skills || []);
  } catch (err) {
    // BE 가 INVALID_QUERY 등 도메인 코드를 정의하지 않아 일반 ApiError 분기로 흡수.
    if (err instanceof NetworkError) {
      showNetBanner('백엔드 서버가 응답하지 않습니다 (http://localhost:8080)');
      renderError(trimmed, '백엔드 서버에 연결할 수 없습니다.');
    } else if (err instanceof ApiError) {
      renderError(trimmed, `매칭에 실패했습니다 (${err.code}: ${err.message})`);
    } else {
      renderError(trimmed, '알 수 없는 오류가 발생했습니다.');
    }
    console.error('[ask-ai] recommend failed', err);
  }
}

export function bindAskAi() {
  const input = $('#intent-input');
  const goBtn = $('#intent-go');

  if (goBtn && input) {
    goBtn.addEventListener('click', () => runQuery(input.value));
  }
  if (input) {
    // Cmd/Ctrl + Enter 로 전송
    input.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault();
        runQuery(input.value);
      }
    });
  }

  // preset 칩
  $$('[data-intent]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const value = btn.dataset.intent || '';
      if (input) input.value = value;
      runQuery(value);
    });
  });

  // 결과 카드 클릭 → 상세 (이벤트 위임)
  const results = $('#intent-results');
  if (results) {
    results.addEventListener('click', (e) => {
      const card = e.target.closest('.intent-match');
      if (!card) return;
      const id = card.dataset.id;
      if (id) openSkillDetail(id);
    });
    results.addEventListener('keydown', (e) => {
      if (e.key !== 'Enter' && e.key !== ' ') return;
      const card = e.target.closest('.intent-match');
      if (!card) return;
      e.preventDefault();
      const id = card.dataset.id;
      if (id) openSkillDetail(id);
    });
  }
}
