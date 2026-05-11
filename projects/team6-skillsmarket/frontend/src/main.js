// 부트스트랩.
//
// 1. 카테고리 칩 + 카드 그리드 + 카드 클릭 핸들러 등록 (discover)
// 2. Ask AI 입력 / preset / 결과 카드 핸들러 등록 (ask-ai)
// 3. 모달 닫기 + 네트워크 배너 닫기
// 4. IntersectionObserver 진입 애니메이션
// 5. 초기 로드: All 카테고리 스킬 목록

import { bindDiscover, loadCategory } from './views/discover.js';
import { bindAskAi } from './views/ask-ai.js';
import { bindCreateSkill } from './views/create-skill.js';
import { bindProgressEvents, restoreProgress } from './views/skill-progress.js';
import { bindModalDismiss, attachReveal, $$ } from './lib/ui.js';

function boot() {
  bindDiscover();
  bindAskAi();
  bindCreateSkill();
  bindProgressEvents();
  bindModalDismiss();
  attachReveal($$('section, .hero'));
  // hero stats 의 tech stacks 는 카테고리 칩 개수에서 자동 계산 (drift 방지).
  const stacks = $$('#category-chips .chip').length;
  const stacksEl = document.getElementById('stat-stacks');
  if (stacksEl) stacksEl.textContent = String(stacks);
  // BE 가 category 를 필수로 요구하므로 첫 칩(Spring Boot) 을 기본 활성화.
  loadCategory('SPRING_BOOT');

  // 새로고침 시 진행 중인 스킬 생성 요청 복원.
  restoreProgress();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot);
} else {
  boot();
}
