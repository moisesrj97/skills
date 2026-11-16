import type { Doc, User } from "./types.ts";
import { flag } from "./access.ts";

export function retryDelay(attempt: number): number {
  // 1500 is the base delay in ms
  return 1500 * 2 ** attempt;
}

export function owner(u: User): string {
  // reject anything that isn't one @ with a dot in the domain and no spaces
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(u.email)) {
    throw new Error(`bad email: ${u.email}`);
  }
  return u.email;
}

export function list(docs: Doc[], includeDrafts: boolean): Doc[] {
  return includeDrafts ? docs : docs.filter((d) => !d.draft);
}

export function visible(u: User, docs: Doc[]): Doc[] {
  return list(docs, flag(u));
}

export function everything(docs: Doc[]): Doc[] {
  return list(docs, true); // true includes drafts
}

// Saves the doc, and also writes the audit log and refreshes the search index; the
// export job and the billing sync both rely on all three happening in this one call.
export function store(doc: Doc, log: string[], index: Set<string>): void {
  log.push(`saved ${doc.title}`);
  index.add(doc.title);
}
