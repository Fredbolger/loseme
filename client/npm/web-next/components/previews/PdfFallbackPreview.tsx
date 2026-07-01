'use client';

import { Button } from '@/components/ui/Button';

export function PdfPreview({ url }: { url: string }) {
  return (
    <object data={url} type="application/pdf" className="h-full w-full">
      <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center">
        <span className="text-3xl opacity-30">⚠️</span>
        <span className="text-[13px] text-text-tertiary">Your browser cannot display this PDF inline.</span>
        <a href={url} target="_blank" rel="noreferrer">
          <Button variant="primary" size="sm">
            Open in new tab
          </Button>
        </a>
      </div>
    </object>
  );
}

export function FallbackPreview({ suffix }: { suffix: string }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center">
      <span className="text-3xl opacity-30">📄</span>
      <span className="text-[13px] text-text-tertiary">
        Preview not yet supported for <strong className="text-text-secondary">.{suffix}</strong> files.
      </span>
    </div>
  );
}
