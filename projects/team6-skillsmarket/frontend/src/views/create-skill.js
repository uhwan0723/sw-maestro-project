// Create Skill 뷰: 스킬 생성 요청 폼.
//
// 유저가 원하는 스킬을 자연어로 작성하고 제출하면 POST /skills/generate 를 호출한다.
// 성공 시 requestId 를 저장하고 진행 상태 뷰로 전환한다.
//
// 검증:
//   - 빈 입력 제출 시 클라이언트 측 validation 메시지
//   - 제출 중 버튼 비활성화 (중복 제출 방지)
//   - API 에러 시 에러 메시지 표시 (NetworkError 배너 활용)

import { generateSkill, ApiError, NetworkError } from '../api/client.js';
import { escapeHtml, $, showNetBanner } from '../lib/ui.js';
import { showProgress } from './skill-progress.js';

let submitting = false;

function setSubmitting(busy) {
  submitting = busy;
  const btn = $('#create-skill-go');
  const spinner = $('#create-skill-spinner');
  if (btn) {
    btn.disabled = busy;
    btn.setAttribute('aria-busy', String(busy));
  }
  if (spinner) {
    spinner.hidden = !busy;
  }
}

function showValidation(message) {
  const el = $('#create-skill-validation');
  if (!el) return;
  el.textContent = message;
  el.hidden = false;
}

function hideValidation() {
  const el = $('#create-skill-validation');
  if (!el) return;
  el.textContent = '';
  el.hidden = true;
}

function showError(message) {
  const el = $('#create-skill-error');
  if (!el) return;
  el.textContent = message;
  el.hidden = false;
}

function hideError() {
  const el = $('#create-skill-error');
  if (!el) return;
  el.textContent = '';
  el.hidden = true;
}

function showSuccess(requestId) {
  const el = $('#create-skill-success');
  if (!el) return;
  el.innerHTML =
    `<span class="create-skill-check">&#10003;</span> ` +
    `스킬 생성 요청이 접수되었습니다. ` +
    `<span class="mono" style="color:var(--accent)">requestId: ${escapeHtml(requestId)}</span>`;
  el.hidden = false;
}

function hideSuccess() {
  const el = $('#create-skill-success');
  if (!el) return;
  el.innerHTML = '';
  el.hidden = true;
}

async function handleSubmit() {
  if (submitting) return;

  hideValidation();
  hideError();
  hideSuccess();

  const input = $('#create-skill-input');
  const trimmed = (input ? input.value : '').trim();

  if (!trimmed) {
    showValidation('스킬 설명을 입력해 주세요.');
    if (input) {
      input.focus();
      input.classList.remove('shake');
      void input.offsetWidth;
      input.classList.add('shake');
    }
    return;
  }

  setSubmitting(true);

  try {
    const data = await generateSkill(trimmed);
    const requestId = data.requestId || data.id || '';

    // requestId 를 sessionStorage 에 저장 (후속 진행 상태 뷰에서 사용).
    if (requestId) {
      try {
        sessionStorage.setItem('lastGenerateRequestId', requestId);
      } catch {
        // storage 사용 불가 시 무시.
      }
    }

    // 입력 초기화
    if (input) input.value = '';

    // 진행 상태 뷰로 전환
    showProgress(requestId);
  } catch (err) {
    if (err instanceof NetworkError) {
      showNetBanner('백엔드 서버가 응답하지 않습니다 (http://localhost:8080)');
      showError('백엔드 서버에 연결할 수 없습니다.');
    } else if (err instanceof ApiError) {
      showError(`스킬 생성 요청에 실패했습니다 (${err.code}: ${err.message})`);
    } else {
      showError('알 수 없는 오류가 발생했습니다.');
    }
    console.error('[create-skill] generateSkill failed', err);
  } finally {
    setSubmitting(false);
  }
}

export function bindCreateSkill() {
  const goBtn = $('#create-skill-go');
  const input = $('#create-skill-input');

  if (goBtn) {
    goBtn.addEventListener('click', handleSubmit);
  }

  if (input) {
    // Cmd/Ctrl + Enter 로 전송
    input.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault();
        handleSubmit();
      }
    });

    // 입력 시 validation 메시지 숨김
    input.addEventListener('input', () => {
      hideValidation();
    });
  }
}
