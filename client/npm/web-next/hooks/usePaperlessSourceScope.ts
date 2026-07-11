'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api-client';
import type {
  PaperlessTag,
  PaperlessCorrespondent,
  PaperlessDocumentType,
  PaperlessSourceScope,
  MonitoredSource,
} from '@/lib/types';

/**
 * TanStack Query hooks for Paperless source scope management.
 * 
 * These hooks manage the filtering configuration for Paperless sources
 * (tags, correspondents, document types).
 */

// Response types from the API
interface AvailableTagsResponse {
  tags: PaperlessTag[];
}

interface AvailableCorrespondentsResponse {
  correspondents: PaperlessCorrespondent[];
}

interface AvailableDocumentTypesResponse {
  document_types: PaperlessDocumentType[];
}

interface EditSourceRequest {
  source_id: string;
  scope_json?: {
    tag_ids?: number[] | null;
    correspondent_ids?: number[] | null;
    document_type_ids?: number[] | null;
  };
}

/**
 * Get all available tags for a specific Paperless connection.
 */
export function useAvailableTagsForSource(connectionId: string | null) {
  return useQuery({
    queryKey: ['paperless', 'tags', 'available', connectionId],
    queryFn: () => api.get<AvailableTagsResponse>(`/paperless/connections/${connectionId}/tags`),
    enabled: !!connectionId,
  });
}

/**
 * Get all available correspondents for a specific Paperless connection.
 */
export function useAvailableCorrespondents(connectionId: string | null) {
  return useQuery({
    queryKey: ['paperless', 'correspondents', 'available', connectionId],
    queryFn: () => api.get<AvailableCorrespondentsResponse>(`/paperless/connections/${connectionId}/correspondents`),
    enabled: !!connectionId,
  });
}

/**
 * Get all available document types for a specific Paperless connection.
 */
export function useAvailableDocumentTypes(connectionId: string | null) {
  return useQuery({
    queryKey: ['paperless', 'document_types', 'available', connectionId],
    queryFn: () => api.get<AvailableDocumentTypesResponse>(`/paperless/connections/${connectionId}/document_types`),
    enabled: !!connectionId,
  });
}

/**
 * Get the current scope configuration for a Paperless source.
 */
export function useSourceScope(source: MonitoredSource | null) {
  return useQuery({
    queryKey: ['sources', source?.id, 'scope'],
    queryFn: async () => {
      if (!source) return null;
      
      // The scope is stored in the source object
      // We need to deserialize it from scope_json if it's a string
      const scopeData = source.scope;
      
      if (!scopeData) return null;
      
      // Handle different scope formats
      if (typeof scopeData === 'string') {
        try {
          const parsed = JSON.parse(scopeData);
          return {
            tag_ids: parsed.tag_ids || null,
            correspondent_ids: parsed.correspondent_ids || null,
            document_type_ids: parsed.document_type_ids || null,
          };
        } catch {
          return null;
        }
      }
      
      // If it's already an object (from the API response)
      if (typeof scopeData === 'object' && scopeData !== null) {
        return {
          tag_ids: (scopeData as any).tag_ids || null,
          correspondent_ids: (scopeData as any).correspondent_ids || null,
          document_type_ids: (scopeData as any).document_type_ids || null,
        };
      }
      
      return null;
    },
    enabled: !!source,
  });
}

/**
 * Extract connection_id from a Paperless source's scope.
 */
export function extractConnectionIdFromSource(source: MonitoredSource | null): string | null {
  if (!source || source.source_type !== 'paperless') return null;
  
  const scopeData = source.scope;
  
  if (!scopeData) return null;
  
  // Handle string scope_json
  if (typeof scopeData === 'string') {
    try {
      const parsed = JSON.parse(scopeData);
      return parsed.connection_id || null;
    } catch {
      return null;
    }
  }
  
  // Handle object scope
  if (typeof scopeData === 'object' && scopeData !== null) {
    return (scopeData as any).connection_id || null;
  }
  
  return null;
}

/**
 * Update a Paperless source's scope configuration.
 */
export function useUpdateSourceScope() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (params: {
      sourceId: string;
      scope: PaperlessSourceScope;
      connectionId: string;
    }) => {
      // Build the scope_json object with connection_id
      const scope_json = {
        type: 'paperless',
        connection_id: params.connectionId,
        ...(params.scope.tag_ids !== null && { tag_ids: params.scope.tag_ids }),
        ...(params.scope.correspondent_ids !== null && { correspondent_ids: params.scope.correspondent_ids }),
        ...(params.scope.document_type_ids !== null && { document_type_ids: params.scope.document_type_ids }),
      };
      
      return api.put<MonitoredSource>(`/sources/edit/${params.sourceId}`, {
        source_id: params.sourceId,
        scope_json,
      });
    },
    onSuccess: (data, variables) => {
      // Invalidate the sources list to refetch
      queryClient.invalidateQueries({
        queryKey: ['sources'],
      });
      // Invalidate the specific source scope
      queryClient.invalidateQueries({
        queryKey: ['sources', variables.sourceId, 'scope'],
      });
    },
  });
}
