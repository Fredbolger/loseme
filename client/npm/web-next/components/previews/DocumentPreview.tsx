'use client';

import { usePreview } from '@/hooks/useSources';
import { LoadingState, ErrorState } from '@/components/ui/States';
import { PlaintextPreview } from './PlaintextPreview';
import { EmailPreview } from './EmailPreview';
import { PdfPreview, FallbackPreview } from './PdfFallbackPreview';
import { PaperlessDocumentHandler } from './PaperlessDocumentHandler';
import { getRuntimeConfig } from '@/lib/api-client';
import { useEffect, useState } from 'react';
import type { PreviewResult } from '@/lib/types';

/**
 * Replaces client/web/static/previews/index.js's RENDERERS array + openPreview().
 * Dispatch is now data-driven off the PreviewResult.preview_type returned by
 * the server, rather than re-deriving file-suffix matching client-side —
 * the server already knows which generator ran, so trust that instead of
 * duplicating the suffix-matching logic in two places (as the old client did
 * between index.js's RENDERERS list and each individual renderer's canHandle).
 */
export function DocumentPreview({ docId, sourcePath }: { docId: string; sourcePath: string }) {
  const preview = usePreview(docId);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [docDetails, setDocDetails] = useState<{connectionId?: string} | null>(null);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);

  const suffix = sourcePath.split('.').pop()?.toLowerCase() || '';
  const isPdf = suffix === 'pdf';

  useEffect(() => {
    if (!isPdf) return;
    getRuntimeConfig().then((cfg) => {
      setPdfUrl(`${cfg.client_url}/api/documents/serve/${docId}`);
    });
  }, [docId, isPdf]);

  if (isPdf) {
    return pdfUrl ? <PdfPreview url={pdfUrl} /> : <LoadingState label="Loading PDF…" />;
  }

  if (preview.isLoading) return <LoadingState label="Loading preview…" />;
  if (preview.isError) return <ErrorState message="Failed to load preview." />;

  const data = preview.data as PreviewResult | undefined;
  if (!data) return <FallbackPreview suffix={suffix} />;

  console.log('DEBUG: [Main] Preview data received:', {
    preview_type: data.preview_type,
    has_paperless_document_id: !!data.paperless_document_id,
    has_connection_id: !!data.connection_id,
    source_path: data.source_path
  });

  switch (data.preview_type) {
    case 'email':
      return (
        <EmailPreview
          subject={data.subject}
          from_={data.from_}
          to={data.to}
          date={data.date}
          body_html={data.body_html}
          body_text={data.body_text}
        />
      );
    case 'plaintext':
      return <PlaintextPreview text={data.text || ''} language={data.language || 'plaintext'} />;
    case 'paperless_document':
    case 'paperless_pdf':
    case 'paperless_image':
      console.log('DEBUG: [Main] Delegating to PaperlessDocumentHandler');
      return (
        <PaperlessDocumentHandler
          data={data}
          docId={docId}
          sourcePath={sourcePath}
        />
      );
    default:
      console.log('DEBUG: [Main] Using fallback preview for type:', data.preview_type);
      return <FallbackPreview suffix={suffix} />;
  }
}
