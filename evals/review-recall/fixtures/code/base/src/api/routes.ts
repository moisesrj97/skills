import { renameNote, listNotes } from '../notes/service';
import { pageCount } from '../notes/pagination';

type Req = { userId: string; params: Record<string, string>; query: Record<string, string>; body: any };

export async function getNotes(req: Req) {
  const limit = Number(req.query.limit ?? 20);
  const notes = await listNotes(req.userId, limit);
  return { notes, pages: pageCount(notes.length, Number(req.query.pageSize ?? 10)) };
}

export async function postRename(req: Req) {
  return renameNote(req.userId, req.params.id, String(req.body.title ?? ''));
}
