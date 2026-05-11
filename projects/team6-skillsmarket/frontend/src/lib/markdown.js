// 외부 라이브러리 없이 SKILL content 를 안전하게 렌더링한다.
//
// 처리 순서:
//   1) 입력 전체를 escapeHtml 한다 (raw HTML 차단).
//   2) escape 된 결과 위에서 화이트리스트 패턴(헤딩/리스트/코드/링크)만
//      미리 정의된 태그로 치환한다.
//   3) 그 외의 모든 입력은 그대로 텍스트로 남는다.
//
// 따라서 server 에서 보낸 content 에 `<script>` 가 있어도 1단계에서
// `&lt;script&gt;` 로 escape 되며, 화이트리스트 패턴에 해당하지 않으므로
// 절대 element 가 되지 않는다.

import { escapeHtml } from './ui.js';

// URL 화이트리스트: http(s):// 로 시작하는 절대 URL 만 허용.
function safeUrl(url) {
  const trimmed = String(url || '').trim();
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  return '#';
}

// 인라인 변환: escape 된 문자열에 대해 동작.
// 순서가 중요하다. 코드 → 링크 순.
function renderInline(escaped) {
  let out = escaped;

  // 인라인 코드: `text`
  out = out.replace(/`([^`\n]+?)`/g, (_, code) => `<code>${code}</code>`);

  // 링크: [text](url)
  // text/url 은 escape 된 상태이므로 추가 변환 없이 사용 가능. URL 만 화이트리스트 검증.
  out = out.replace(
    /\[([^\]]+)\]\(([^)\s]+)\)/g,
    (_, text, url) => {
      // url 은 escape 되었으므로 `&amp;` 같은 시퀀스를 원형으로 되돌릴 필요는 없다.
      // safeUrl 은 스킴만 본다.
      const href = safeUrl(url);
      return `<a href="${href}" target="_blank" rel="noopener noreferrer">${text}</a>`;
    }
  );

  return out;
}

export function renderMarkdown(input) {
  if (input === null || input === undefined || input === '') return '';
  const escaped = escapeHtml(input);
  const lines = escaped.split('\n');

  const out = [];
  let i = 0;
  let inList = false;
  let inCodeBlock = false;
  let codeBuffer = [];

  const closeList = () => {
    if (inList) {
      out.push('</ul>');
      inList = false;
    }
  };

  while (i < lines.length) {
    const line = lines[i];

    // 펜스 코드 블록 ``` ... ```
    // escapeHtml 은 backtick(`) 을 변환하지 않으므로 그대로 매칭 가능.
    if (/^```/.test(line)) {
      if (!inCodeBlock) {
        closeList();
        inCodeBlock = true;
        codeBuffer = [];
      } else {
        out.push(`<pre><code>${codeBuffer.join('\n')}</code></pre>`);
        inCodeBlock = false;
        codeBuffer = [];
      }
      i++;
      continue;
    }

    if (inCodeBlock) {
      codeBuffer.push(line);
      i++;
      continue;
    }

    // 헤딩: # ## ###
    const heading = /^(#{1,3})\s+(.+)$/.exec(line);
    if (heading) {
      closeList();
      const level = heading[1].length;
      out.push(`<h${level}>${renderInline(heading[2])}</h${level}>`);
      i++;
      continue;
    }

    // 순서 없는 리스트: - / * 둘 다 허용
    const li = /^\s*[-*]\s+(.+)$/.exec(line);
    if (li) {
      if (!inList) {
        out.push('<ul>');
        inList = true;
      }
      out.push(`<li>${renderInline(li[1])}</li>`);
      i++;
      continue;
    }

    // 빈 줄
    if (/^\s*$/.test(line)) {
      closeList();
      i++;
      continue;
    }

    // 일반 단락
    closeList();
    out.push(`<p>${renderInline(line)}</p>`);
    i++;
  }

  // 미닫힘 처리
  closeList();
  if (inCodeBlock) {
    out.push(`<pre><code>${codeBuffer.join('\n')}</code></pre>`);
  }

  return out.join('\n');
}
