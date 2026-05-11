// Skill Generation Progress 뷰: SSE 실시간 진행 상태 표시.
//
// EventSource 로 /skills/generate/{requestId}/stream 을 구독하여
// 각 단계(PENDING → CLARIFYING → GENERATING → REVIEWING → REFINING → COMPLETED)를
// 실시간으로 업데이트한다.
//
// SSE 연결 끊김 시 GET /skills/generate/{requestId} 폴링으로 fallback.
// 페이지 새로고침 시 sessionStorage 의 requestId 로 상태를 복원한다.

import { API_BASE } from '../config.js';
import { getGenerationStatus, NetworkError } from '../api/client.js';
import { $, showNetBanner, showToast } from '../lib/ui.js';
import { renderMarkdown } from '../lib/markdown.js';

const STEPS = ['PENDING', 'CLARIFYING', 'GENERATING', 'REVIEWING', 'REFINING', 'COMPLETED'];

const STEP_LABELS = {
  PENDING: '요청 대기 중',
  CLARIFYING: '요구사항 분석',
  GENERATING: '스킬 생성',
  REVIEWING: '품질 리뷰',
  REFINING: '최종 수정',
  COMPLETED: '완료',
};

let currentRequestId = null;
let eventSource = null;
let pollTimer = null;
let currentStatus = null;

// ── public API ──

/** 진행 상태 뷰를 활성화하고 SSE 구독을 시작한다. */
export function showProgress(requestId) {
  if (!requestId) return;
  currentRequestId = requestId;
  currentStatus = null;

  // 폼 숨기고 프로그레스 표시
  const formWrap = $('#create-skill-form-wrap');
  const progressWrap = $('#skill-progress-wrap');
  if (formWrap) formWrap.hidden = true;
  if (progressWrap) progressWrap.hidden = false;

  // 초기 UI 리셋
  renderSteps('PENDING');
  hideProgressError();
  hideProgressResult();

  // SSE 연결
  connectSSE(requestId);
}

/** 진행 상태 뷰를 닫고 폼으로 복귀한다. */
export function hideProgress() {
  disconnect();
  currentRequestId = null;
  currentStatus = null;

  const formWrap = $('#create-skill-form-wrap');
  const progressWrap = $('#skill-progress-wrap');
  if (formWrap) formWrap.hidden = false;
  if (progressWrap) progressWrap.hidden = true;
}

/** boot() 에서 호출: 새로고침 시 sessionStorage 에 저장된 requestId 복원. */
export function restoreProgress() {
  let requestId = null;
  try {
    requestId = sessionStorage.getItem('lastGenerateRequestId');
  } catch {
    return;
  }
  if (!requestId) return;

  // 폴링으로 현재 상태를 확인한 뒤 진행 중이면 뷰를 연다.
  restoreFromServer(requestId);
}

/** 바인딩: 재시도 / 새 스킬 만들기 버튼 이벤트. */
export function bindProgressEvents() {
  const retryBtn = $('#progress-retry-btn');
  if (retryBtn) {
    retryBtn.addEventListener('click', handleRetry);
  }
  const newBtn = $('#progress-new-btn');
  if (newBtn) {
    newBtn.addEventListener('click', handleNewSkill);
  }
}

// ── SSE ──

function connectSSE(requestId) {
  disconnect(); // 기존 연결 정리

  const url = `${API_BASE}/skills/generate/${encodeURIComponent(requestId)}/stream`;
  eventSource = new EventSource(url);

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      handleStatusUpdate(data.status, data);
    } catch {
      // 파싱 실패 시 무시.
    }
  };

  eventSource.onerror = () => {
    // SSE 연결 끊김 → fallback 폴링.
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
    startPolling(requestId);
  };

  // SSE emitter는 파이프라인 시작 후에 생성되므로 초기 이벤트가 유실될 수 있다.
  // SSE와 폴링을 병행하여 놓친 상태 변경을 보완한다.
  startPolling(requestId);
}

// ── Polling fallback ──

function startPolling(requestId) {
  if (pollTimer) return; // 이미 폴링 중
  pollTimer = setInterval(() => pollStatus(requestId), 3000);
  // 즉시 한 번 실행
  pollStatus(requestId);
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

async function pollStatus(requestId) {
  try {
    const data = await getGenerationStatus(requestId);
    handleStatusUpdate(data.status, data);
  } catch (err) {
    if (err instanceof NetworkError) {
      showNetBanner('백엔드 서버가 응답하지 않습니다 (http://localhost:8080)');
    }
    // 폴링은 계속 시도
  }
}

// ── 상태 복원 (새로고침) ──

async function restoreFromServer(requestId) {
  try {
    const data = await getGenerationStatus(requestId);
    const status = data.status;

    if (status === 'COMPLETED' || status === 'FAILED') {
      // 이미 종료된 요청 → sessionStorage 정리, 폼 표시 유지
      clearRequestId();
      return;
    }

    // 진행 중 → 프로그레스 뷰 표시 + SSE 재연결
    showProgress(requestId);
    handleStatusUpdate(status, data);
  } catch {
    // 서버 오류 또는 404 → 정리
    clearRequestId();
  }
}

// ── 상태 처리 ──

function handleStatusUpdate(status, data) {
  if (!status) return;

  // 같은 상태면 무시
  if (status === currentStatus) return;
  currentStatus = status;

  renderSteps(status);

  if (status === 'COMPLETED') {
    disconnect();
    clearRequestId();
    showProgressResult(data);
  } else if (status === 'FAILED') {
    disconnect();
    clearRequestId();
    showProgressError();
  }
}

// ── UI 렌더링 ──

function renderSteps(activeStatus) {
  const activeIdx = STEPS.indexOf(activeStatus);

  STEPS.forEach((step, idx) => {
    const el = $(`#progress-step-${step}`);
    if (!el) return;

    const indicator = el.querySelector('.progress-step-indicator');
    const label = el.querySelector('.progress-step-label');

    // 상태 클래스 초기화
    el.classList.remove('done', 'active', 'pending', 'failed');

    if (activeStatus === 'FAILED') {
      // FAILED: 현재까지 완료된 단계는 done, 실패한 단계는 failed
      if (idx < activeIdx) {
        el.classList.add('done');
        if (indicator) indicator.textContent = '\u2713';
      } else {
        el.classList.add('failed');
        if (indicator) indicator.textContent = '!';
      }
    } else if (idx < activeIdx) {
      el.classList.add('done');
      if (indicator) indicator.textContent = '\u2713';
    } else if (idx === activeIdx) {
      el.classList.add('active');
      if (indicator) indicator.innerHTML = '<span class="progress-spinner"></span>';
      // COMPLETED 는 체크마크로 표시
      if (step === 'COMPLETED') {
        el.classList.remove('active');
        el.classList.add('done');
        if (indicator) indicator.textContent = '\u2713';
      }
    } else {
      el.classList.add('pending');
      if (indicator) indicator.textContent = String(idx + 1);
    }
  });

  // 상태 텍스트 업데이트
  const statusText = $('#progress-status-text');
  if (statusText) {
    if (activeStatus === 'FAILED') {
      statusText.textContent = '스킬 생성에 실패했습니다.';
    } else if (activeStatus === 'COMPLETED') {
      statusText.textContent = '스킬 생성이 완료되었습니다!';
    } else {
      statusText.textContent = STEP_LABELS[activeStatus] || '처리 중...';
    }
  }
}

function showProgressError() {
  const el = $('#progress-error');
  if (el) el.hidden = false;
  const result = $('#progress-result');
  if (result) result.hidden = true;
}

function hideProgressError() {
  const el = $('#progress-error');
  if (el) el.hidden = true;
}

function showProgressResult(data) {
  const el = $('#progress-result');
  if (!el) return;
  el.hidden = false;

  const rawMarkdown = data.finalSkillContent || '';

  // 완료 메시지 + 복사 버튼 + 마크다운 렌더링 결과
  el.innerHTML =
    '<div class="progress-complete-msg">' +
      '<span class="create-skill-check">&#10003;</span> ' +
      '스킬 생성이 완료되었습니다.' +
    '</div>' +
    '<div class="progress-result-wrap">' +
      '<div class="progress-result-toolbar">' +
        '<span class="progress-result-title">Generated Skill</span>' +
        '<button type="button" class="btn progress-copy-btn" id="progress-copy-btn">' +
          '<span>copy</span>' +
        '</button>' +
      '</div>' +
      '<div class="progress-result-content modal-content">' +
        renderMarkdown(rawMarkdown) +
      '</div>' +
    '</div>';

  // 복사 버튼 바인딩
  const copyBtn = $('#progress-copy-btn');
  if (copyBtn) {
    copyBtn.addEventListener('click', () => {
      navigator.clipboard.writeText(rawMarkdown).then(
        () => showToast('클립보드에 복사되었습니다!'),
        () => showToast('복사에 실패했습니다. 수동으로 복사해 주세요.')
      );
    });
  }
}

function hideProgressResult() {
  const el = $('#progress-result');
  if (el) {
    el.hidden = true;
    el.innerHTML = '';
  }
}

// ── 버튼 핸들러 ──

function handleRetry() {
  // 마지막 requestId 로 재시도 — 사용자가 다시 폼에서 제출하도록 안내
  hideProgress();
}

function handleNewSkill() {
  hideProgress();
}

// ── 유틸 ──

function disconnect() {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
  stopPolling();
}

function clearRequestId() {
  try {
    sessionStorage.removeItem('lastGenerateRequestId');
  } catch {
    // ignore
  }
}
