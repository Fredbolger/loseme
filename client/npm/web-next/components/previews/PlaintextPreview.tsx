'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const MARKDOWN_LANGS = new Set(['markdown', 'restructuredtext']);

export function PlaintextPreview({ text, language }: { text: string; language: string }) {
  const isMarkdown = MARKDOWN_LANGS.has(language);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-border px-4 py-2">
        <span className="font-mono text-[10px] uppercase tracking-wide text-accent-primary">
          {language}
        </span>
        <span className="font-mono text-[10px] text-text-tertiary">{text.split('\n').length} lines</span>
      </div>

      {isMarkdown ? (
        <div className="prose prose-sm max-w-none flex-1 overflow-auto px-5 py-4 prose-headings:font-display prose-headings:text-text-primary prose-p:text-text-secondary prose-a:text-accent-primary prose-code:rounded prose-code:bg-bg-tertiary prose-code:px-1 prose-code:text-accent-secondary prose-pre:bg-bg-tertiary">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
        </div>
      ) : (
        <pre className="flex-1 overflow-auto whitespace-pre-wrap break-words px-5 py-4 font-mono text-[12px] leading-relaxed text-text-primary">
          {text}
        </pre>
      )}
    </div>
  );
}
