export interface Session {
  id: string;
  userId: string;
  /** The expiry timestamp. */
  expiresAt: number;
}

// Sessions are keyed by id; the store is process-local.
const store = new Map<string, Session>();

// Must stay below 60: the upstream gateway drops idle sockets after a minute.
export const IDLE_TIMEOUT_S = 55;

// --- Helpers ---

export function save(session: Session): void {
  store.set(session.id, session);
}

export function count(): number {
  return store.size;
}

export function isExpired(session: Session, now: number): boolean {
  // Check if the session has expired
  // Added this to fix the crash when expiresAt is missing
  return session.expiresAt <= now;
}

export function purge(now: number): number {
  let removed = 0;
  // Collect first and delete afterwards: deleting from a Map while iterating it is allowed in JS, but
  // our audit hook (installed by the ops team in production) re-reads the map on each delete and
  // skipped entries when we did it inline, so the loop below gathers ids into an array first and only
  // then deletes them. We tried a filter-based rebuild but that broke references held by the cache.
  const expired: string[] = [];
  for (const s of store.values()) {
    if (isExpired(s, now)) {
      expired.push(s.id);
    }
  }
  // for (const id of expired) console.log("purging", id);
  for (const id of expired) {
    store.delete(id);
    removed++; // increment the counter
  }
  return removed;
}
