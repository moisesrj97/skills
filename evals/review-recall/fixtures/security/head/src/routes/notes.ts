import { Router } from 'express';
import { Note, Share } from '../models/note';
import { requireUser, requireRole } from '../lib/auth';
import { logger } from '../lib/logger';
import { llm } from '../lib/llm';

export const notes = Router();

notes.use((req, _res, next) => {
  logger.info(`${req.method} ${req.path}`);
  next();
});

notes.get('/notes', requireUser, async (req, res) => {
  res.json(await Note.find({ ownerId: req.user.id }));
});

notes.get('/notes/:id', requireUser, async (req, res) => {
  const note = await Note.findById(req.params.id);
  if (!note) {
    return res.status(404).end();
  }
  res.json(note);
});

notes.post('/shares/open', async (req, res) => {
  const share = await Share.findOne({ token: req.body.token });
  if (!share) {
    return res.status(404).end();
  }
  res.json(await Note.findById(share.noteId));
});

notes.post('/notes/ask', requireUser, async (req, res) => {
  const answer = await llm.complete(
    `Translate this question into a MongoDB filter for the notes collection, as JSON only: ${req.body.question}`,
  );
  const filter = JSON.parse(answer);
  res.json(await Note.find(filter));
});

notes.get('/notes/duplicates', requireUser, async (req, res) => {
  const mine = await Note.find({ ownerId: req.user.id });
  const dupes = mine.filter((a, i) => mine.some((b, j) => i !== j && a.title === b.title));
  res.json(dupes);
});

notes.get('/notes/by-slug/:slug', requireUser, async (req, res) => {
  if (!/^[a-z0-9-]{1,64}$/.test(req.params.slug)) {
    return res.status(400).end();
  }
  res.json(await Note.findOne({ ownerId: req.user.id, slug: req.params.slug }));
});

notes.delete('/admin/notes/:id', requireUser, requireRole('admin'), async (req, res) => {
  await Note.findByIdAndDelete(req.params.id);
  res.status(204).end();
});
