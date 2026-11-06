import { Router } from 'express';
import { Note } from '../models/note';
import { requireUser } from '../lib/auth';

export const notes = Router();

notes.get('/notes', requireUser, async (req, res) => {
  res.json(await Note.find({ ownerId: req.user.id }));
});
