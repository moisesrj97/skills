type Props = { note: { title: string; html: string } };

export function PublicNote({ note }: Props) {
  return (
    <article>
      <h1>{note.title}</h1>
      <div dangerouslySetInnerHTML={{ __html: note.html }} />
    </article>
  );
}
