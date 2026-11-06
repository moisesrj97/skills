export interface Note {
  id: string;
  ownerId: string;
  title: string;
  archived?: boolean;
}

const notes = new Map<string, Note>();

export async function getNote(id: string): Promise<Note | undefined> {
  return notes.get(id);
}

export async function saveNote(note: Note): Promise<void> {
  notes.set(note.id, note);
}

export async function allNotes(): Promise<Note[]> {
  return [...notes.values()];
}
