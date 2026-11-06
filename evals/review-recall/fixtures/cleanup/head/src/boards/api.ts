import { request } from '../shared/httpClient';

export type Board = { id: string; title: string; slug: string };
export type User = { id: string; name: string };
export type Settings = { pageSize: number };

export const getUser = (id: string) => request<User>(`/api/users/${id}`);
export const getSettings = (id: string) => request<Settings>(`/api/users/${id}/settings`);
export const getBoards = (userId: string) => request<Board[]>(`/api/users/${userId}/boards`);
