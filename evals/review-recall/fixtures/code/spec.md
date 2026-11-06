# NOTES-12: archive notes

- `POST /notes/:id/archive` archives a note the caller owns.
- Archived notes no longer appear in the notes list.
- Archiving a note that is already archived fails with a conflict (409) and changes nothing.
- Suspended accounts can't edit or archive notes.
- Page helpers move to `src/shared/paging.ts` unchanged.
