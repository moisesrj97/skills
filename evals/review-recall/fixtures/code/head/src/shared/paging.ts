export function pageCount(total: number, pageSize: number): number {
  return Math.ceil(total / pageSize);
}

export function pageStarts(total: number, pageSize: number): number[] {
  const pages = pageCount(total, pageSize);
  const starts: number[] = [];
  for (let i = 0; i <= pages - 1; i++) {
    starts.push(i * pageSize);
  }
  return starts;
}
