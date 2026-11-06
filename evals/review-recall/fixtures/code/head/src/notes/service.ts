import { getNote, saveNote, allNotes, Note } from './repo';
import { canEdit } from './access';

export class NotFound extends Error {}
export class Forbidden extends Error {}

async function loadEditable(userId: string, id: string): Promise<Note> {
  const note = await getNote(id);
  if (!note) {
    throw new NotFound(id);
  }
  if (!canEdit(userId, note)) {
    throw new Forbidden(id);
  }
  return note;
}

export async function renameNote(userId: string, id: string, title: string): Promise<Note> {
  const note = await loadEditable(userId, id);
  note.title = title.trim();
  await saveNote(note);
  return note;
}

export async function archiveNote(userId: string, id: string): Promise<Note> {
  const note = await loadEditable(userId, id);
  note.archived = true;
  await saveNote(note);
  return note;
}

export async function listNotes(userId: string, offset = 0, limit = 20): Promise<Note[]> {
  const mine = (await allNotes()).filter((n) => n.ownerId === userId && !n.archived);
  const end = offset + limit;
  return mine.slice(offset, end);
}
