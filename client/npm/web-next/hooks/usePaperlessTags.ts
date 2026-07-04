'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api-client';
import type { PaperlessTag, DocumentTagData } from '@/lib/types';

/**
 * TanStack Query hooks for Paperless tag management.
 * 
 * These hooks communicate directly with the FastAPI backend.
 * Do NOT introduce a Next.js route handler - Paperless operations do not require
 * device-local access unlike filesystem or mailbox previews.
 * 
 * This is an intentional architectural distinction: Paperless is server-side only,
 * so all operations go through the FastAPI backend which handles authentication
 * and communication with the Paperless-ngx API.
 */

// Error types for better type safety
export interface PaperlessApiError {
  detail: 'paperless_unreachable' | 'paperless_document_missing' | 'paperless_auth_failed' | string;
}

/**
 * Get all available tags for a specific Paperless connection.
 * Used for autocomplete in the TagEditor component.
 */
export function useAvailableTags(connectionId: string | null) {
  return useQuery({
    queryKey: ['paperless', 'tags', 'available', connectionId],
    queryFn: () => api.get<{ tags: PaperlessTag[] }>(`/paperless/tags?connection_id=${connectionId}`),
    enabled: !!connectionId,
  });
}

/**
 * Get the current tags for a specific document part.
 * Only works for Paperless documents (source_type === 'paperless').
 */
export function useDocumentTags(documentPartId: string | null) {
  return useQuery({
    queryKey: ['paperless', 'documents', documentPartId, 'tags'],
    queryFn: () => api.get<DocumentTagData>(`/paperless/documents/${documentPartId}/tags`),
    enabled: !!documentPartId,
  });
}

/**
 * Create a new Paperless tag.
 * Returns the created tag which can then be immediately assigned to a document.
 */
export function useCreateTag() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (params: { connectionId: string; name: string; color?: string }) =>
      api.post<PaperlessTag>(`/paperless/tags`, {
        connection_id: params.connectionId,
        name: params.name,
        color: params.color,
      }),
    onSuccess: (newTag, variables) => {
      // Invalidate the available tags for this connection
      queryClient.invalidateQueries({
        queryKey: ['paperless', 'tags', 'available', variables.connectionId],
      });
    },
  });
}

/**
 * Add a tag to a document.
 * Uses optimistic updates for immediate UI feedback.
 */
export function useAddTag() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (params: { documentPartId: string; tagId: number }) =>
      api.post<DocumentTagData>(`/paperless/documents/${params.documentPartId}/tags`, {
        tag_id: params.tagId,
      }),
    onMutate: async (params) => {
      // Cancel any outgoing refetches to avoid overwriting optimistic update
      await queryClient.cancelQueries({
        queryKey: ['paperless', 'documents', params.documentPartId, 'tags'],
      });
      
      // Snapshot the previous value
      const previousTags = queryClient.getQueryData<DocumentTagData>([
        'paperless', 'documents', params.documentPartId, 'tags',
      ]);
      
      // Optimistically update to the new value
      queryClient.setQueryData<DocumentTagData>(
        ['paperless', 'documents', params.documentPartId, 'tags'],
        (old) => {
          if (!old) return old;
          
          // Check if tag is already present
          const tagIds = [...old.tag_ids];
          const tags = [...old.tags];
          
          if (!tagIds.includes(params.tagId)) {
            tagIds.push(params.tagId);
            // Add a placeholder tag for the UI (will be replaced by real data on success)
            tags.push({
              id: params.tagId,
              name: `Tag ${params.tagId}`,
              color: undefined,
            });
          }
          
          return {
            ...old,
            tag_ids: tagIds,
            tags: tags,
          };
        }
      );
      
      // Return a context object with the snapshotted value
      return { previousTags };
    },
    onError: (err, params, context) => {
      // Rollback to the previous value on error
      if (context?.previousTags) {
        queryClient.setQueryData<DocumentTagData>(
          ['paperless', 'documents', params.documentPartId, 'tags'],
          context.previousTags
        );
      }
    },
    onSettled: (data, error, params) => {
      // Invalidate the query to refetch fresh data
      queryClient.invalidateQueries({
        queryKey: ['paperless', 'documents', params.documentPartId, 'tags'],
      });
    },
  });
}

/**
 * Remove a tag from a document.
 * Uses optimistic updates for immediate UI feedback.
 */
export function useRemoveTag() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (params: { documentPartId: string; tagId: number }) =>
      api.delete<DocumentTagData>(`/paperless/documents/${params.documentPartId}/tags/${params.tagId}`),
    onMutate: async (params) => {
      // Cancel any outgoing refetches to avoid overwriting optimistic update
      await queryClient.cancelQueries({
        queryKey: ['paperless', 'documents', params.documentPartId, 'tags'],
      });
      
      // Snapshot the previous value
      const previousTags = queryClient.getQueryData<DocumentTagData>([
        'paperless', 'documents', params.documentPartId, 'tags',
      ]);
      
      // Optimistically update to the new value
      queryClient.setQueryData<DocumentTagData>(
        ['paperless', 'documents', params.documentPartId, 'tags'],
        (old) => {
          if (!old) return old;
          
          // Remove the tag with the specified ID
          const tagIds = old.tag_ids.filter(id => id !== params.tagId);
          const tags = old.tags.filter(tag => tag.id !== params.tagId);
          
          return {
            ...old,
            tag_ids: tagIds,
            tags: tags,
          };
        }
      );
      
      // Return a context object with the snapshotted value
      return { previousTags };
    },
    onError: (err, params, context) => {
      // Rollback to the previous value on error
      if (context?.previousTags) {
        queryClient.setQueryData<DocumentTagData>(
          ['paperless', 'documents', params.documentPartId, 'tags'],
          context.previousTags
        );
      }
    },
    onSettled: (data, error, params) => {
      // Invalidate the query to refetch fresh data
      queryClient.invalidateQueries({
        queryKey: ['paperless', 'documents', params.documentPartId, 'tags'],
      });
    },
  });
}