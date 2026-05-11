import { test } from 'node:test';
import assert from 'node:assert';
import { renderMarkdown } from '../../src/lib/markdown.js';

test('renderMarkdown returns empty for null/undefined/empty', () => {
  assert.strictEqual(renderMarkdown(null), '');
  assert.strictEqual(renderMarkdown(undefined), '');
  assert.strictEqual(renderMarkdown(''), '');
});

test('plain text becomes <p>', () => {
  const out = renderMarkdown('hello world');
  assert.match(out, /^<p>hello world<\/p>$/);
});

test('headings render h1/h2/h3', () => {
  assert.match(renderMarkdown('# Title'), /^<h1>Title<\/h1>$/);
  assert.match(renderMarkdown('## Sub'), /^<h2>Sub<\/h2>$/);
  assert.match(renderMarkdown('### Small'), /^<h3>Small<\/h3>$/);
});

test('unordered list - and *', () => {
  const dash = renderMarkdown('- item1\n- item2');
  assert.match(dash, /<ul>\s*<li>item1<\/li>\s*<li>item2<\/li>\s*<\/ul>/);
  const star = renderMarkdown('* a\n* b');
  assert.match(star, /<ul>\s*<li>a<\/li>\s*<li>b<\/li>\s*<\/ul>/);
});

test('inline code wraps in <code>', () => {
  const out = renderMarkdown('use `npm test`');
  assert.match(out, /<p>use <code>npm test<\/code><\/p>/);
});

test('fence code block wraps in <pre><code>', () => {
  const out = renderMarkdown('```\nconst x = 1;\n```');
  assert.match(out, /<pre><code>const x = 1;<\/code><\/pre>/);
});

test('link with http URL allowed', () => {
  const out = renderMarkdown('[home](https://example.com)');
  assert.match(out, /<a href="https:\/\/example\.com" target="_blank" rel="noopener noreferrer">home<\/a>/);
});

test('javascript: URL is rewritten to # (XSS guard)', () => {
  const out = renderMarkdown('[click](javascript:alert(1))');
  assert.match(out, /<a href="#"/);
  assert.doesNotMatch(out, /javascript:/);
});

test('raw HTML is escaped, not rendered', () => {
  const out = renderMarkdown('<script>alert(1)</script>');
  // 어떤 형태로든 실제 <script> 태그가 만들어지면 안 된다.
  assert.doesNotMatch(out, /<script>/);
  assert.match(out, /&lt;script&gt;/);
});

test('mixed content: heading + list + code', () => {
  const input = '# Title\n\n- one\n- two\n\n```\ncode\n```';
  const out = renderMarkdown(input);
  assert.match(out, /<h1>Title<\/h1>/);
  assert.match(out, /<ul>\s*<li>one<\/li>\s*<li>two<\/li>\s*<\/ul>/);
  assert.match(out, /<pre><code>code<\/code><\/pre>/);
});

test('list closes before paragraph', () => {
  const out = renderMarkdown('- item\n\nparagraph');
  // <ul> 닫힌 다음 <p> 시작
  assert.match(out, /<\/ul>[\s\S]*<p>paragraph<\/p>/);
});
