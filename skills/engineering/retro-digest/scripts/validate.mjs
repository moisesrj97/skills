// Inlined into the review page by build-review-page.mjs, so it must stay one self-contained function.
export function validateReview(digest, review) {
  const errors = [];
  const decisions = review?.decisions ?? {};
  const known = new Map([
    ...digest.clusters.map((c) => [c.id, ['apply', 'reject', 'open']]),
    ...(digest.recurring ?? []).map((r) => [r.id, ['reopen', 'fold']]),
  ]);
  for (const [id, allowed] of known) {
    if (!allowed.includes(decisions[id])) {
      errors.push(`${id}: pick one of ${allowed.join(', ')}`);
    }
  }
  for (const id of Object.keys(decisions)) {
    if (!known.has(id)) {
      errors.push(`${id}: not in this digest`);
    }
  }
  return errors;
}
