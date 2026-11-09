#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { validateReview } from './validate.mjs';

const TEMPLATE = path.join(path.dirname(fileURLToPath(import.meta.url)), 'review.html');

export function buildReviewPage(digest) {
  // `<\/` keeps a "</script>" inside the digest's text from closing the page's script tag.
  const data = JSON.stringify(digest).replaceAll('</', '<\\/');
  return fs
    .readFileSync(TEMPLATE, 'utf8')
    .replace('/*DIGEST*/null', () => data)
    .replace('/*VALIDATE*/', () => validateReview.toString());
}

function main() {
  const [digestPath, outPath] = process.argv.slice(2);
  if (!digestPath || !outPath) {
    console.error('usage: build-review-page.mjs <digest.json> <out.html>');
    process.exit(2);
  }
  const digest = JSON.parse(fs.readFileSync(digestPath, 'utf8'));
  fs.writeFileSync(outPath, buildReviewPage(digest));
  console.log(path.resolve(outPath));
}

if (process.argv[1] && fs.realpathSync(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main();
}
