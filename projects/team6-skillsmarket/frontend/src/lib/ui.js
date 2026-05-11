// 공용 UI 유틸. XSS 방어용 escapeHtml 와 모달 / 배너 헬퍼를 모은다.
//
// 모든 서버에서 받은 텍스트는 DOM 삽입 전 `escapeHtml`을 거쳐야 한다.
// markdown content 만 lib/markdown.js 의 화이트리스트 변환을 사용한다 (후속 작업).

const ESCAPE_MAP = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
};

export function escapeHtml(value) {
  if (value === null || value === undefined) return '';
  return String(value).replace(/[&<>"']/g, (c) => ESCAPE_MAP[c]);
}

// querySelector shortcut
export const $ = (selector, root = document) => root.querySelector(selector);
export const $$ = (selector, root = document) =>
  Array.from(root.querySelectorAll(selector));

// IntersectionObserver 진입 애니메이션
export function attachReveal(elements) {
  if (!('IntersectionObserver' in window)) {
    elements.forEach((el) => el.classList.add('in'));
    return;
  }
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add('in');
          io.unobserve(e.target);
        }
      });
    },
    { threshold: 0.1 }
  );
  elements.forEach((el) => {
    el.classList.add('reveal');
    io.observe(el);
  });
}

// 상단 네트워크 배너 표시 / 숨김
export function showNetBanner(message) {
  const banner = document.getElementById('net-banner');
  if (!banner) return;
  const text = banner.querySelector('.net-banner-text');
  if (text) text.textContent = message;
  banner.hidden = false;
}

export function hideNetBanner() {
  const banner = document.getElementById('net-banner');
  if (!banner) return;
  banner.hidden = true;
}

// 모달 헬퍼: ESC + 백드롭 클릭으로 닫힘. content 는 이미 sanitize 된 HTML 문자열.
let modalEscHandler = null;

export function openModal(htmlContent) {
  const modal = document.getElementById('skill-modal');
  const body = document.getElementById('modal-content');
  if (!modal || !body) return;
  body.innerHTML = htmlContent;
  modal.hidden = false;
  modal.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';

  modalEscHandler = (e) => {
    if (e.key === 'Escape') closeModal();
  };
  document.addEventListener('keydown', modalEscHandler);
}

export function closeModal() {
  const modal = document.getElementById('skill-modal');
  const body = document.getElementById('modal-content');
  if (!modal) return;
  modal.hidden = true;
  modal.setAttribute('aria-hidden', 'true');
  if (body) body.innerHTML = '';
  document.body.style.overflow = '';
  if (modalEscHandler) {
    document.removeEventListener('keydown', modalEscHandler);
    modalEscHandler = null;
  }
}

// 토스트 메시지 표시 (자동 소멸)
export function showToast(message, durationMs = 2500) {
  // 기존 토스트 제거
  const prev = document.getElementById('ui-toast');
  if (prev) prev.remove();

  const toast = document.createElement('div');
  toast.id = 'ui-toast';
  toast.className = 'ui-toast';
  toast.textContent = message;
  document.body.appendChild(toast);

  // 강제 reflow 후 show 클래스 추가 (애니메이션)
  void toast.offsetWidth;
  toast.classList.add('show');

  setTimeout(() => {
    toast.classList.remove('show');
    toast.addEventListener('transitionend', () => toast.remove(), { once: true });
    // fallback: transitionend 미발생 시 직접 제거
    setTimeout(() => { if (toast.parentNode) toast.remove(); }, 400);
  }, durationMs);
}

export function bindModalDismiss() {
  const modal = document.getElementById('skill-modal');
  if (!modal) return;
  modal.addEventListener('click', (e) => {
    const target = e.target;
    if (target instanceof Element && target.hasAttribute('data-close')) {
      closeModal();
    }
  });
  const banner = document.getElementById('net-banner');
  if (banner) {
    const closeBtn = banner.querySelector('.net-banner-close');
    if (closeBtn) closeBtn.addEventListener('click', hideNetBanner);
  }
}
