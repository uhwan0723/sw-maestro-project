// Skill 상세 모달.
//
// BE 실제 응답 shape (2026-05-09 정렬):
//   { id, title, description, category, content }
//   - status / tags 필드 미제공 → statusPill 조건부 표시, tags 는 빈 배열로 fallback
//   - content: markdown 본문 (null 가능)
//
// 모든 텍스트는 escapeHtml 후 삽입. content 만 markdown.js 의 화이트리스트 변환을
// 거친다. 백드롭 / ESC / X 버튼으로 닫힘.

import { getSkill, ApiError, NetworkError } from '../api/client.js';
import { escapeHtml, openModal, showNetBanner, showToast } from '../lib/ui.js';
import { renderMarkdown } from '../lib/markdown.js';

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

function renderDetailBody(skill) {
  const categoryLabel = CATEGORY_LABEL[skill.category] || skill.category || '';
  const tagsHtml = (skill.tags || [])
    .map((t) => `<span class="skill-tag">${escapeHtml(t)}</span>`)
    .join('');

  const contentHtml = skill.content
    ? renderMarkdown(skill.content)
    : '<p style="color:var(--fg-3)">본문이 아직 작성되지 않았습니다.</p>';

  return `
    <header class="modal-head">
      <div class="modal-eyebrow">
        ${statusPill(skill.status)}
        <span class="skill-tag">${escapeHtml(categoryLabel)}</span>
      </div>
      <h2 class="modal-title" id="modal-title">${escapeHtml(skill.title)}</h2>
      <p class="modal-desc">${escapeHtml(skill.description)}</p>
      ${tagsHtml ? `<div class="modal-tags">${tagsHtml}</div>` : ''}
    </header>
    <div class="modal-body">
      ${skill.content ? '<div class="modal-content-toolbar"><button type="button" class="btn progress-copy-btn" id="detail-copy-btn"><span>copy</span></button></div>' : ''}
      <div class="modal-content">${contentHtml}</div>
    </div>
  `;
}

function renderError(message) {
  return `
    <header class="modal-head">
      <h2 class="modal-title" id="modal-title">오류</h2>
    </header>
    <div class="modal-body">
      <div class="modal-error">${escapeHtml(message)}</div>
    </div>
  `;
}

export async function openSkillDetail(id) {
  // 우선 로딩 상태로 모달을 띄운다.
  openModal(`
    <header class="modal-head">
      <h2 class="modal-title" id="modal-title">불러오는 중...</h2>
    </header>
    <div class="modal-body">
      <div class="modal-error" style="color:var(--fg-3)">스킬 상세를 가져오고 있습니다.</div>
    </div>
  `);

  try {
    const skill = await getSkill(id);
    openModal(renderDetailBody(skill));

    // content 복사 버튼 바인딩
    const copyBtn = document.getElementById('detail-copy-btn');
    if (copyBtn) {
      copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(skill.content).then(
          () => showToast('클립보드에 복사되었습니다!'),
          () => showToast('복사에 실패했습니다. 수동으로 복사해 주세요.'),
        );
      });
    }
  } catch (err) {
    // BE 가 IllegalArgumentException 을 매핑하지 않아 404 가 500 으로 떨어짐 →
    // 별도 404 분기 없이 일반 ApiError 분기로 흡수.
    if (err instanceof NetworkError) {
      showNetBanner('백엔드 서버가 응답하지 않습니다 (http://localhost:8080)');
      openModal(renderError('백엔드 서버에 연결할 수 없습니다.'));
    } else if (err instanceof ApiError) {
      openModal(renderError(`스킬 상세를 불러오지 못했습니다 (${err.code}: ${err.message})`));
    } else {
      openModal(renderError('알 수 없는 오류가 발생했습니다.'));
    }
    console.error('[skill-detail] openSkillDetail failed', err);
  }
}
