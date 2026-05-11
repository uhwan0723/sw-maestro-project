import { test } from 'node:test';
import assert from 'node:assert';
import { escapeHtml } from '../../src/lib/ui.js';

test('escapeHtml escapes 5 special chars', () => {
  assert.strictEqual(escapeHtml('<script>'), '&lt;script&gt;');
  assert.strictEqual(escapeHtml('a&b'), 'a&amp;b');
  assert.strictEqual(escapeHtml('"hello"'), '&quot;hello&quot;');
  assert.strictEqual(escapeHtml("it's"), 'it&#39;s');
});

test('escapeHtml combines all 5 chars', () => {
  assert.strictEqual(
    escapeHtml(`<a href="x" title='y'>&z</a>`),
    '&lt;a href=&quot;x&quot; title=&#39;y&#39;&gt;&amp;z&lt;/a&gt;'
  );
});

test('escapeHtml handles null/undefined/empty', () => {
  assert.strictEqual(escapeHtml(null), '');
  assert.strictEqual(escapeHtml(undefined), '');
  assert.strictEqual(escapeHtml(''), '');
});

test('escapeHtml coerces non-string input', () => {
  assert.strictEqual(escapeHtml(42), '42');
  assert.strictEqual(escapeHtml(true), 'true');
});
