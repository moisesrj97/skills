// Inlined into the review page by build-review-page.mjs, so it must stay one self-contained function.
export function validateReview(digest, review) {
  const errors = [];
  const decisions = review?.decisions ?? {};
  const known = new Map([
    ...digest.clusters.map((c) => [c.id, ['apply', 'reject', 'open']]),
    ...(digest.recurring ?? []).map((r) => [r.id, ['reopen', 'fold']]),
  ]);
  for (const [id, allowed] of known) {
    const d = decisions[id];
    if (!d || !allowed.includes(d.decision)) {
      errors.push(`${id}: pick one of ${allowed.join(', ')}`);
    } else if (d.decision === 'reject' && !d.note?.trim()) {
      errors.push(`${id}: a rejection needs a reason`);
    }
  }
  for (const id of Object.keys(decisions)) {
    if (!known.has(id)) {
      errors.push(`${id}: not in this digest`);
    }
  }
  for (const entry of digest.plan ?? []) {
    const needsTicket =
      entry.ticket && entry.items.some((id) => ['apply', 'reopen'].includes(decisions[id]?.decision));
    if (needsTicket && !review.tickets?.[entry.repo]?.trim()) {
      errors.push(`${entry.repo}: give a ticket or write "create"`);
    }
  }
  return errors;
}
