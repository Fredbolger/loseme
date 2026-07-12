'use client';

import { useState, useEffect } from 'react';
import { PaperlessPreview, PaperlessFallbackPreview } from './PaperlessPreview';
import type { PreviewResult } from '@/lib/types';

/**
 * Handles the complete lifecycle of paperless document preview:
 * 1. Extracts document ID from direct fields or source_path
 * 2. Extracts connection ID from direct fields or meta
 * 3. Renders the appropriate preview component
 */
export function PaperlessDocumentHandler({
  data,
  docId,
  sourcePath,
}: {
  data: PreviewResult;
  docId: string;
  sourcePath: string;
}) {
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [connectionId, setConnectionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const initializePreview = async () => {
      try {
        console.log('DEBUG: [Handler] Initializing paperless preview for docId:', docId);
        console.log('DEBUG: [Handler] Input data:', {
          preview_type: data.preview_type,
          paperless_document_id: data.paperless_document_id,
          connection_id: data.connection_id,
          source_path: data.source_path,
          has_meta: !!data.meta,
        });
        
        // Step 1: Get document ID (from direct field, then fallback to source_path)
        let extractedDocId = data.paperless_document_id;
        let sourcePath = data.source_path;
        
        // Fallback: extract from source_path if not directly available
        if (!extractedDocId && sourcePath) {
          const parts = sourcePath.split(':');
          if (parts.length >= 2) {
            extractedDocId = parts[1];
            console.log('DEBUG: Extracted document ID from source_path:', extractedDocId);
          }
        }
        
        // Fallback: try meta.source_path
        if (!extractedDocId && data.meta?.source_path) {
          const parts = String(data.meta.source_path).split(':');
          if (parts.length >= 2) {
            extractedDocId = parts[1];
            console.log('DEBUG: Extracted document ID from meta.source_path:', extractedDocId);
          }
        }
        
        // Step 2: Get connection ID (from direct field, then fallback to meta)
        let connId = data.connection_id;
        
        // Fallback: try to extract from meta.scope_json
        if (!connId && data.meta?.scope_json) {
          try {
            const scope = typeof data.meta.scope_json === 'string' 
              ? JSON.parse(data.meta.scope_json) 
              : data.meta.scope_json;
            connId = scope.connection_id;
            console.log('DEBUG: Extracted connection ID from meta.scope_json:', connId);
          } catch (e) {
            console.error('DEBUG: Failed to parse scope JSON from meta:', e);
          }
        }
        
        console.log('DEBUG: [Handler] Extracted IDs - paperlessDocumentId:', extractedDocId, 'connectionId:', connId);
        setDocumentId(extractedDocId || null);
        setConnectionId(connId || null);
        
      } catch (initError) {
        console.error('DEBUG: Error initializing paperless preview:', initError);
        setError('Failed to initialize preview');
      }
    };
    
    initializePreview();
  }, [data, docId]);

  console.log('DEBUG: [Handler] Current state - documentId:', documentId, 'connectionId:', connectionId);

  if (error) {
    console.log('DEBUG: [Handler] Showing fallback due to error:', error);
    return <PaperlessFallbackPreview sourcePath={sourcePath} />;
  }

  if (documentId && connectionId) {
    console.log('DEBUG: [Handler] Rendering PaperlessPreview with', { documentId, connectionId });
    return (
      <PaperlessPreview
        paperlessDocumentId={documentId}
        connectionId={connectionId}
        sourcePath={data.source_path || sourcePath}
        previewType={data.preview_type}
      />
    );
  }

  console.log('DEBUG: [Handler] Missing parameters, showing fallback. documentId:', documentId, 'connectionId:', connectionId);
  return <PaperlessFallbackPreview sourcePath={sourcePath} />;
}