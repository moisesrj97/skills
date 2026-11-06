import { getNote, saveNote, allNotes, Note } from './repo';
import { canEdit } from './access';

export class NotFound extends Error {}
export class Forbidden extends Error {}

export async function renameNote(userId: string, id: string, title: string): Promise<Note> {
  const note = await getNote(id);
  if (!note) {
    throw new NotFound(id);
  }
  if (!canEdit(userId, note)) {
    throw new Forbidden(id);
  }
  if (title.trim().length === 0) {
    throw new Error('empty title');
  }
  note.title = title.trim();
  await saveNote(note);
  return note;
}

export async function listNotes(userId: string, limit: number): Promise<Note[]> {
  const mine = (await allNotes()).filter((n) => n.ownerId === userId);
  return mine.slice(0, limit);
}
