import { getUser, getSettings, getBoards } from './api';

export type DashboardOptions = { pageSize?: number };

export async function loadDashboard(userId: string, opts: DashboardOptions = {}) {
  const user = await getUser(userId);
  const settings = await getSettings(userId);
  const boards = await getBoards(userId);
  const cards = boards.slice(0, resolvePageSize(opts, settings.pageSize)).map((board) => {
    const slug = board.title
      .toLowerCase()
      .normalize('NFKD')
      .replace(/[^\w\s-]/g, '')
      .trim()
      .replace(/[\s_-]+/g, '-');
    return { ...board, href: `/boards/${slug}` };
  });

  // return the greeting and the cards
  return { greeting: `Hi ${user.name}`, cards };
}

export function resolvePageSize(opts: DashboardOptions, fallback: number): number {
  return opts.pageSize || fallback;
}
