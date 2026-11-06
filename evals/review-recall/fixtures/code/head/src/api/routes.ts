import { renameNote, listNotes, archiveNote } from '../notes/service';
import { pageCount } from '../shared/paging';

type Req = { userId: string; params: Record<string, string>; query: Record<string, string>; body: any };

export async function getNotes(req: Req) {
  const limit = Number(req.query.limit ?? 20);
  const notes = await listNotes(req.userId, limit);
  return { notes, pages: pageCount(notes.length, Number(req.query.pageSize ?? 10)) };
}

export async function postRename(req: Req) {
  const title = String(req.body.title ?? '');
  return renameNote(req.userId, req.params.id, title);
}

export async function postArchive(req: Req) {
  return archiveNote(req.userId, req.params.id);
}
