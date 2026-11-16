export interface Session {
  id: string;
  userId: string;
}

// Sessions are keyed by id; the store is process-local.
const store = new Map<string, Session>();

export function save(session: Session): void {
  store.set(session.id, session);
}

export function count(): number {
  return store.size;
}
