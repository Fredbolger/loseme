'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/Button';
import { LoadingState, ErrorState } from '@/components/ui/States';
import { getRuntimeConfig } from '@/lib/api-client';
import { useDocumentTags } from '@/hooks/usePaperlessTags';
import { Badge } from '@/components/ui/Badge';
import type { PaperlessTag } from '@/lib/types';

/**
 * Paperless document preview component.
 * 
 * This component handles previewing of Paperless-ngx documents by:
 * 1. Fetching the document from the server's paperless proxy endpoint
 * 2. Displaying the document content (PDF, image, or other formats)
 * 3. Providing fallback options if direct preview is not possible
 * 4. Displaying document tags with names and colors
 */
export function PaperlessPreview({
  paperlessDocumentId,
  connectionId,
  sourcePath,
  previewType,
  docId,
}: {
  paperlessDocumentId: string;
  connectionId: string;
  sourcePath: string;
  previewType: string;
  docId?: string;
}) {
  const [documentUrl, setDocumentUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Fetch tags for this document
  const documentPartId = docId || paperlessDocumentId;
  const { data: documentTags, isLoading: isLoadingTags } = useDocumentTags(documentPartId);

  useEffect(() => {
    const fetchDocument = async () => {
      try {
        setIsLoading(true);
        setError(null);

        // Get runtime config for API URL and key
        const config = await getRuntimeConfig();

        // Fetch the document from the paperless proxy endpoint
        const headers: HeadersInit = {
          'Content-Type': 'application/json',
        };
        
        if (config.api_key) {
          headers['X-API-Key'] = config.api_key;
        }

        const response = await fetch(
          `${config.api_url}/paperless/documents/${paperlessDocumentId}/proxy?connection_id=${connectionId}`,
          { headers }
        );

        if (!response.ok) {
          throw new Error(`Failed to fetch document: ${response.status} ${response.statusText}`);
        }

        // Create a blob URL for the document
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        setDocumentUrl(url);

      } catch (err) {
        console.error('Error fetching paperless document:', err);
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setIsLoading(false);
      }
    };

    fetchDocument();

    // Cleanup blob URL on unmount
    return () => {
      if (documentUrl) {
        URL.revokeObjectURL(documentUrl);
      }
    };
  }, [paperlessDocumentId, connectionId]);

  if (isLoading) {
    return <LoadingState label="Loading Paperless document…" />;
  }

  if (error) {
    return <ErrorState message={`Failed to load Paperless document: ${error}`} />;
  }

  if (!documentUrl) {
    return <ErrorState message="No document URL available" />;
  }

  // Determine the preview approach based on the preview type
  const isPdf = previewType === 'paperless_pdf' || previewType === 'paperless_document';
  const isImage = previewType === 'paperless_image';

  return (
    <div className="flex h-full flex-col">
      {/* Document preview area */}
      <div className="flex-1 overflow-auto">
        {isPdf ? (
          <object 
            data={documentUrl} 
            type="application/pdf" 
            className="h-full w-full" 
            aria-label="Paperless document PDF preview"
          >
            <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center">
              <span className="text-3xl opacity-30">📄</span>
              <span className="text-[13px] text-text-tertiary">
                Your browser cannot display this PDF inline.
              </span>
              <a href={documentUrl} target="_blank" rel="noreferrer">
                <Button variant="primary" size="sm">
                  Open PDF in new tab
                </Button>
              </a>
            </div>
          </object>
        ) : isImage ? (
          <img 
            src={documentUrl} 
            alt={sourcePath.split(':').slice(2).join(':') || 'Paperless document'} 
            className="max-w-full max-h-full object-contain" 
          />
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center">
            <span className="text-3xl opacity-30">📄</span>
            <span className="text-[13px] text-text-tertiary">
              Document preview available for download
            </span>
            <a href={documentUrl} target="_blank" rel="noreferrer">
              <Button variant="primary" size="sm">
                Download Document
              </Button>
            </a>
          </div>
        )}
      </div>

      {/* Document info footer */}
      <div className="border-t border-border-primary p-3 text-xs">
        <div className="truncate text-text-tertiary">
          {sourcePath.split(':').slice(2).join(':') || 'Paperless Document'}
        </div>
        <div className="flex items-center gap-2 mt-2">
          {/* Display tags with colors */}
          {isLoadingTags ? null : documentTags?.tags?.length ? (
            documentTags.tags.map((tag: PaperlessTag) => (
              <Badge
                key={tag.id}
                dot={tag.color || undefined}
                className="text-[11px]"
                style={{
                  backgroundColor: tag.color || undefined,
                  color: tag.text_color || undefined
                }}
              >
                {tag.name}
              </Badge>
            ))
          ) : (
            <span className="text-text-quaternary">No tags</span>
          )}
        </div>
        <div className="text-text-quaternary mt-1">
          Paperless ID: {paperlessDocumentId}
        </div>
      </div>
    </div>
  );
}

/**
 * Fallback preview for paperless documents when specific preview type is unknown
 */
export function PaperlessFallbackPreview({ sourcePath }: { sourcePath: string }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center">
      <span className="text-3xl opacity-30">📋</span>
      <span className="text-[13px] text-text-tertiary">
        Paperless document preview not available
      </span>
      <span className="text-xs text-text-quaternary break-words max-w-full">
        {sourcePath}
      </span>
    </div>
  );
}