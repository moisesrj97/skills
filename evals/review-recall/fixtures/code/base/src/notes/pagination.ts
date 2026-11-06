export function pageCount(total: number, pageSize: number): number {
  if (pageSize <= 0) {
    throw new Error('pageSize must be positive');
  }
  return Math.ceil(total / pageSize);
}
