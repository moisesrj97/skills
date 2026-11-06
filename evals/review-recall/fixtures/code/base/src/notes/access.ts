import { Note } from './repo';

export function canEdit(userId: string, note: Note): boolean {
  return note.ownerId === userId;
}
