const suspended = new Set<string>();

export async function isSuspended(userId: string): Promise<boolean> {
  return suspended.has(userId);
}
