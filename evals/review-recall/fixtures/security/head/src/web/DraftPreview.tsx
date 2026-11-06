import { useState } from 'react';
import { marked } from 'marked';

export function DraftPreview() {
  const [text, setText] = useState('');
  return (
    <div>
      <textarea value={text} onChange={(e) => setText(e.target.value)} />
      <div className="preview" dangerouslySetInnerHTML={{ __html: marked.parse(text) as string }} />
    </div>
  );
}
