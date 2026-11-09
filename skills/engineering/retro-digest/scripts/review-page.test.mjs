import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';
import { buildReviewPage } from './build-review-page.mjs';
import { validateReview } from './validate.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const digest = JSON.parse(fs.readFileSync(path.join(here, 'example-digest.json'), 'utf8'));

const complete = () => ({ decisions: { C1: 'apply', C2: 'reject', 'R-A': 'fold' } });

test('a complete review passes', () => {
  assert.deepEqual(validateReview(digest, complete()), []);
});

test('every cluster and recurring item needs a valid decision', () => {
  const review = complete();
  delete review.decisions.C1;
  review.decisions['R-A'] = 'apply';
  assert.deepEqual(validateReview(digest, review), [
    'C1: pick one of apply, reject, open',
    'R-A: pick one of reopen, fold',
  ]);
});

test('ids outside the digest fail', () => {
  const review = complete();
  review.decisions.C9 = 'apply';
  assert.deepEqual(validateReview(digest, review), ['C9: not in this digest']);
});

const pageScript = (html) => html.match(/<script>([\s\S]*)<\/script>/)[1];

test('the built page embeds the digest and the validator as valid JS', () => {
  const html = buildReviewPage(digest);
  assert.doesNotMatch(html, /\/\*DIGEST\*\/|\/\*VALIDATE\*\//);
  assert.match(html, /function validateReview/);
  assert.doesNotThrow(() => new vm.Script(pageScript(html)));
});

test('text in the digest cannot close the page script', () => {
  const hostile = structuredClone(digest);
  hostile.clusters[0].proposal = '</script><script>alert(1)</script> and $& $1';
  const script = pageScript(buildReviewPage(hostile));
  assert.match(script, /<\\\/script>/);
  assert.match(script, /\$& \$1/);
  assert.doesNotThrow(() => new vm.Script(script));
});
