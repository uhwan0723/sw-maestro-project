// API base URL.
//
// BE 실제 명세는 prefix 없이 `/skills` 로 매핑되어 있어 base 도 origin 까지만.
// 운영자는 브라우저 콘솔에서
//
//   window.SKILLS_API_BASE = 'https://api.example.com';
//
// 으로 새로고침 전에 덮어써서 다른 서버를 가리킬 수 있다.
//
// 주의: 끝에 슬래시(`/`)는 두지 않는다. api wrapper 가 path 를 `/skills` 형태로
// 붙이기 때문이다.
export const API_BASE =
  (typeof window !== 'undefined' && window.SKILLS_API_BASE) ||
  'http://localhost:8080';
