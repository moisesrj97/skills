import { Schema, model, Types } from 'mongoose';

const noteSchema = new Schema({
  ownerId: { type: Types.ObjectId, required: true },
  title: String,
  html: String,
  public: { type: Boolean, default: false },
});

export const Note = model('Note', noteSchema);

const shareSchema = new Schema({ noteId: Types.ObjectId, token: String });
export const Share = model('Share', shareSchema);
