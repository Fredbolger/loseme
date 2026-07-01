'use client';

interface EmailPreviewProps {
  subject?: string;
  from_?: string;
  to?: string;
  date?: string;
  body_html?: string;
  body_text?: string;
}

export function EmailPreview({ subject, from_, to, date, body_html, body_text }: EmailPreviewProps) {
  const dateStr = date ? new Date(date).toLocaleString() : '—';

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-col gap-1.5 border-b border-border px-5 py-4">
        <HeaderRow label="From" value={from_} />
        <HeaderRow label="To" value={to} />
        <HeaderRow label="Date" value={dateStr} />
        <HeaderRow label="Subject" value={subject} emphasis />
      </div>

      <div className="flex-1 overflow-hidden">
        {body_html ? (
          <iframe
            srcDoc={body_html}
            sandbox=""
            className="h-full w-full border-0 bg-white"
            title="Email body"
          />
        ) : (
          <pre className="h-full overflow-auto whitespace-pre-wrap break-words px-5 py-4 font-mono text-[12px] leading-relaxed text-text-primary">
            {body_text || ''}
          </pre>
        )}
      </div>
    </div>
  );
}

function HeaderRow({ label, value, emphasis }: { label: string; value?: string; emphasis?: boolean }) {
  return (
    <div className="flex gap-3 font-mono text-[12px]">
      <span className="w-14 flex-shrink-0 text-text-tertiary">{label}</span>
      <span className={emphasis ? 'font-semibold text-text-primary' : 'break-words text-text-primary'}>
        {value || '—'}
      </span>
    </div>
  );
}
