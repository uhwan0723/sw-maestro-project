// Discover 뷰: 카테고리 칩 + 카드 그리드.
//
// 카테고리 칩 ↔ 백엔드 enum 매핑 (BE 실제 명세, 2026-05-09 정렬):
//   "Spring Boot"      → "SPRING_BOOT"
//   "Frontend / React" → "REACT"
//   "DevOps"           → "DEVOPS"
//   "Data"             → "DATA"
//   "ETC"              → "ETC"
//
// BE 가 category 를 필수로 요구하므로 All 칩은 제거됨. 모든 enum 은 UPPER_SNAKE.

import { getSkills, ApiError, NetworkError } from '../api/client.js';
import { escapeHtml, $, $$, showNetBanner } from '../lib/ui.js';
import { openSkillDetail } from './skill-detail.js';

// 라벨 매핑 (서버에서 받은 enum 값을 사람이 보기 쉬운 라벨로)
const CATEGORY_LABEL = {
  SPRING_BOOT: 'Spring Boot',
  REACT: 'React',
  DEVOPS: 'DevOps',
  DATA: 'Data',
  ETC: 'ETC',
};

// status 가 응답에 없으면 빈 문자열 — BE 가 status 필드 추가하면 자동으로 다시 표시됨.
function statusPill(status) {
  if (!status) return '';
  const cls = status === 'DONE' ? 'status-done' : 'status-progress';
  return `<span class="status-pill ${cls}">${escapeHtml(status)}</span>`;
}

function renderCard(skill) {
  const tagsHtml = (skill.tags || [])
    .slice(0, 3)
    .map((t) => `<span class="skill-tag">${escapeHtml(t)}</span>`)
    .join('');

  const categoryLabel = CATEGORY_LABEL[skill.category] || skill.category || '';

  // skill-foot 에 카테고리 라벨 + 태그 갯수 표시.
  const tagCount = (skill.tags || []).length;
  return `
    <div class="skill" data-id="${escapeHtml(skill.id)}" tabindex="0" role="button" aria-label="${escapeHtml(skill.title)} 상세 보기">
      <div class="skill-head">
        ${statusPill(skill.status)}
        <span class="skill-tag">${escapeHtml(categoryLabel)}</span>
      </div>
      <div class="skill-name">${escapeHtml(skill.title)}</div>
      <div class="skill-desc">${escapeHtml(skill.description)}</div>
      <div class="skill-foot">
        <span>${tagsHtml || '<span style="color:var(--fg-3)">no tags</span>'}</span>
        <span>${tagCount} tag${tagCount === 1 ? '' : 's'}</span>
      </div>
    </div>
  `;
}

function renderEmptyMessage(message) {
  const empty = $('#skill-grid-empty');
  const grid = $('#skill-grid');
  if (!empty || !grid) return;
  grid.innerHTML = '';
  empty.hidden = false;
  empty.textContent = message;
}

function renderError(message) {
  renderEmptyMessage(message);
}

function renderSkills(skills) {
  const grid = $('#skill-grid');
  const empty = $('#skill-grid-empty');
  if (!grid || !empty) return;

  // hero stats: 현재 카테고리에 보이는 카드 수 (in view).
  const total = (skills || []).length;
  const stat = document.getElementById('stat-total');
  if (stat) stat.textContent = String(total);

  if (total === 0) {
    renderEmptyMessage('이 카테고리에 등록된 스킬이 없습니다');
    return;
  }
  empty.hidden = true;
  empty.textContent = '';
  // 한 줄에 3개씩 채워 보이도록 — 모자란 자리는 빈 placeholder 로 채운다.
  const cards = skills.map(renderCard).join('');
  const remainder = skills.length % 3;
  const placeholders = remainder === 0
    ? ''
    : Array.from({ length: 3 - remainder }, () =>
        '<div class="skill-placeholder" aria-hidden="true"></div>'
      ).join('');
  grid.innerHTML = cards + placeholders;
}

export async function loadCategory(category) {
  const grid = $('#skill-grid');
  const empty = $('#skill-grid-empty');
  if (grid) grid.innerHTML = '';
  if (empty) {
    empty.hidden = false;
    empty.textContent = '불러오는 중...';
  }
  try {
    const data = await getSkills(category);
    renderSkills(data.skills || []);
  } catch (err) {
    if (err instanceof NetworkError) {
      showNetBanner(
        '백엔드 서버가 응답하지 않습니다 (http://localhost:8080)'
      );
      renderError('백엔드 서버에 연결할 수 없습니다. 서버 실행 후 새로고침하세요.');
    } else if (err instanceof ApiError) {
      renderError(`스킬 목록을 불러오지 못했습니다 (${err.code}: ${err.message})`);
    } else {
      renderError('알 수 없는 오류가 발생했습니다.');
    }
    console.error('[discover] loadCategory failed', err);
  }
}

export function bindDiscover() {
  const chips = $$('#category-chips .chip');
  chips.forEach((chip) => {
    chip.addEventListener('click', () => {
      chips.forEach((c) => {
        c.classList.remove('active');
        c.setAttribute('aria-selected', 'false');
      });
      chip.classList.add('active');
      chip.setAttribute('aria-selected', 'true');
      loadCategory(chip.dataset.cat);
    });
  });

  // 카드 클릭 → 상세 모달 (이벤트 위임)
  const grid = $('#skill-grid');
  if (grid) {
    grid.addEventListener('click', (e) => {
      const card = e.target.closest('.skill');
      if (!card) return;
      const id = card.dataset.id;
      if (id) openSkillDetail(id);
    });
    grid.addEventListener('keydown', (e) => {
      if (e.key !== 'Enter' && e.key !== ' ') return;
      const card = e.target.closest('.skill');
      if (!card) return;
      e.preventDefault();
      const id = card.dataset.id;
      if (id) openSkillDetail(id);
    });
  }
}
