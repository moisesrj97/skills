import { Note } from './repo';
import { isSuspended } from '../shared/accounts';

export async function canEdit(userId: string, note: Note): Promise<boolean> {
  if (await isSuspended(userId)) {
    return false;
  }
  return note.ownerId === userId;
}
