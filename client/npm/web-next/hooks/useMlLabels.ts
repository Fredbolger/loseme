'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api-client';
import type { 
  MlLabelDefinition, 
  MlLabelOption, 
  MlDocumentLabel 
} from '@/lib/types';

/**
 * TanStack Query hooks for ML label management.
 * 
 * These hooks communicate directly with the FastAPI backend.
 * ML labels are 100% local to LoSeMe and work with any source type,
 * unlike Paperless tags which are proxied through the Paperless API.
 * 
 * This is an intentional architectural distinction: ML labels are meant
 * to become ML training targets and must never be conflated with Paperless's
 * own tag system in the UI or the data model.
 */

// Error types for better type safety
export interface MlLabelsApiError {
  detail: 'label_definition_not_found' | 'label_option_not_found' | 'label_assignment_not_found' | 'invalid_value_type' | string;
}

// =============================================================================
// Label Definitions
// =============================================================================

/**
 * Create a new label definition.
 */
export function useCreateLabelDefinition() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (params: {
      key: string;
      name: string;
      value_type: 'select' | 'multiselect' | 'text' | 'boolean' | 'number';
      description?: string | null;
      color?: string | null;
    }) => api.post<MlLabelDefinition>('/ml-labels/definitions', {
      key: params.key,
      name: params.name,
      value_type: params.value_type,
      description: params.description,
      color: params.color,
    }),
    onSuccess: () => {
      // Invalidate all label definition queries
      queryClient.invalidateQueries({ queryKey: ['ml-labels', 'definitions'] });
    },
  });
}

/**
 * List all label definitions.
 */
export function useLabelDefinitions(activeOnly: boolean = true) {
  return useQuery({
    queryKey: ['ml-labels', 'definitions', { activeOnly }],
    queryFn: () => api.get<MlLabelDefinition[]>(`/ml-labels/definitions?active_only=${activeOnly}`),
  });
}

/**
 * Get a single label definition by ID.
 */
export function useLabelDefinition(definitionId: string | null) {
  return useQuery({
    queryKey: ['ml-labels', 'definitions', definitionId],
    queryFn: () => api.get<MlLabelDefinition>(`/ml-labels/definitions/${definitionId}`),
    enabled: !!definitionId,
  });
}

/**
 * Update an existing label definition.
 */
export function useUpdateLabelDefinition() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (params: {
      definitionId: string;
      key?: string;
      name?: string;
      description?: string | null;
      value_type?: 'select' | 'multiselect' | 'text' | 'boolean' | 'number';
      color?: string | null;
      is_active?: boolean;
    }) => api.put<MlLabelDefinition>(`/ml-labels/definitions/${params.definitionId}`, {
      key: params.key,
      name: params.name,
      description: params.description,
      value_type: params.value_type,
      color: params.color,
      is_active: params.is_active,
    }),
    onSuccess: (_, variables) => {
      // Invalidate the specific definition and the list
      queryClient.invalidateQueries({ queryKey: ['ml-labels', 'definitions', variables.definitionId] });
      queryClient.invalidateQueries({ queryKey: ['ml-labels', 'definitions'] });
    },
  });
}

/**
 * Delete a label definition.
 */
export function useDeleteLabelDefinition() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (definitionId: string) => 
      api.delete<{ status: string; definition_id: string }>(`/ml-labels/definitions/${definitionId}`),
    onSuccess: (_, definitionId) => {
      // Invalidate all label definition queries
      queryClient.invalidateQueries({ queryKey: ['ml-labels', 'definitions'] });
      // Also invalidate any document label queries that might reference this definition
      queryClient.invalidateQueries({ queryKey: ['ml-labels', 'documents'] });
    },
  });
}

// =============================================================================
// Label Options
// =============================================================================

/**
 * List all options for a label definition.
 */
export function useLabelOptions(definitionId: string | null) {
  return useQuery({
    queryKey: ['ml-labels', 'options', definitionId],
    queryFn: () => api.get<MlLabelOption[]>(`/ml-labels/definitions/${definitionId}/options`),
    enabled: !!definitionId,
  });
}

/**
 * Create a new option for a label definition.
 */
export function useCreateLabelOption() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (params: {
      definitionId: string;
      value: string;
      display_name: string;
      color?: string | null;
      sort_order?: number;
    }) => api.post<MlLabelOption>(`/ml-labels/definitions/${params.definitionId}/options`, {
      value: params.value,
      display_name: params.display_name,
      color: params.color,
      sort_order: params.sort_order ?? 0,
    }),
    onSuccess: (_, variables) => {
      // Invalidate the options for this definition
      queryClient.invalidateQueries({ queryKey: ['ml-labels', 'options', variables.definitionId] });
    },
  });
}

/**
 * Delete a label option.
 */
export function useDeleteLabelOption() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (optionId: string) => 
      api.delete<{ status: string; option_id: string }>(`/ml-labels/options/${optionId}`),
    onSuccess: (_, optionId) => {
      // We don't know which definition this option belonged to, so invalidate all options
      queryClient.invalidateQueries({ queryKey: ['ml-labels', 'options'] });
      // Also invalidate document label queries as assignments might be affected
      queryClient.invalidateQueries({ queryKey: ['ml-labels', 'documents'] });
    },
  });
}

// =============================================================================
// Document Label Assignments
// =============================================================================

/**
 * Get all label assignments for a document.
 */
export function useDocumentLabels(documentPartId: string | null) {
  return useQuery({
    queryKey: ['ml-labels', 'documents', documentPartId],
    queryFn: () => api.get<MlDocumentLabel[]>(`/ml-labels/documents/${documentPartId}`),
    enabled: !!documentPartId,
  });
}

/**
 * Assign a label to a document.
 * Uses optimistic updates for immediate UI feedback.
 */
export function useAssignLabel() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (params: {
      documentPartId: string;
      definitionId: string;
      optionId?: string | null;
      textValue?: string | null;
      numberValue?: number | null;
      boolValue?: boolean | null;
      confidence?: number | null;
      labelSource?: 'human' | 'model';
    }) => api.post<MlDocumentLabel>(`/ml-labels/documents/${params.documentPartId}`, {
      definition_id: params.definitionId,
      option_id: params.optionId,
      text_value: params.textValue,
      number_value: params.numberValue,
      bool_value: params.boolValue,
      confidence: params.confidence,
      label_source: params.labelSource ?? 'human',
    }),
    onMutate: async (params) => {
      // Cancel any outgoing refetches to avoid overwriting optimistic update
      await queryClient.cancelQueries({
        queryKey: ['ml-labels', 'documents', params.documentPartId],
      });
      
      // Snapshot the previous value
      const previousLabels = queryClient.getQueryData<MlDocumentLabel[]>([
        'ml-labels', 'documents', params.documentPartId,
      ]);
      
      // Get the definition to know what type of label this is
      const definitions = queryClient.getQueryData<MlLabelDefinition[]>([
        'ml-labels', 'definitions', { activeOnly: true },
      ]) || [];
      
      const definition = definitions.find(d => d.id === params.definitionId);
      
      // Optimistically update to the new value
      queryClient.setQueryData<MlDocumentLabel[]>([
        'ml-labels', 'documents', params.documentPartId
      ], (old) => {
        if (!old) return old;
        
        const newLabels = [...old];
        const newLabel: MlDocumentLabel = {
          id: `optimistic-${Date.now()}`,
          document_part_id: params.documentPartId,
          definition_id: params.definitionId,
          option_id: params.optionId ?? null,
          text_value: params.textValue ?? null,
          number_value: params.numberValue ?? null,
          bool_value: params.boolValue ?? null,
          confidence: params.confidence ?? null,
          label_source: params.labelSource ?? 'human',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          // We may not have these yet, but add placeholders
          definition_key: definition?.key,
          definition_name: definition?.name,
          definition_value_type: definition?.value_type,
          definition_color: definition?.color,
        };
        
        if (definition && definition.value_type !== 'multiselect') {
          // For single-valued types, replace any existing label with the same definition_id
          const index = newLabels.findIndex(l => l.definition_id === params.definitionId);
          if (index !== -1) {
            newLabels[index] = newLabel;
          } else {
            newLabels.push(newLabel);
          }
        } else {
          // For multiselect, just add the new label
          newLabels.push(newLabel);
        }
        
        return newLabels;
      });
      
      // Return a context object with the snapshotted value
      return { previousLabels };
    },
    onError: (err, params, context) => {
      // Rollback to the previous value on error
      if (context?.previousLabels) {
        queryClient.setQueryData<MlDocumentLabel[]>([
          'ml-labels', 'documents', params.documentPartId
        ], context.previousLabels);
      }
    },
    onSettled: (data, error, params) => {
      // Invalidate the query to refetch fresh data
      queryClient.invalidateQueries({
        queryKey: ['ml-labels', 'documents', params.documentPartId],
      });
    },
  });
}

/**
 * Remove a label assignment from a document.
 * Uses optimistic updates for immediate UI feedback.
 */
export function useRemoveLabelAssignment() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (params: {
      documentPartId: string;
      assignmentId: string;
    }) => api.delete<{ status: string; assignment_id: string }>(
      `/ml-labels/documents/${params.documentPartId}/${params.assignmentId}`
    ),
    onMutate: async (params) => {
      // Cancel any outgoing refetches to avoid overwriting optimistic update
      await queryClient.cancelQueries({
        queryKey: ['ml-labels', 'documents', params.documentPartId],
      });
      
      // Snapshot the previous value
      const previousLabels = queryClient.getQueryData<MlDocumentLabel[]>([
        'ml-labels', 'documents', params.documentPartId,
      ]);
      
      // Optimistically update to the new value
      queryClient.setQueryData<MlDocumentLabel[]>([
        'ml-labels', 'documents', params.documentPartId
      ], (old) => {
        if (!old) return old;
        
        // Remove the label with the specified ID
        return old.filter(label => label.id !== params.assignmentId);
      });
      
      // Return a context object with the snapshotted value
      return { previousLabels };
    },
    onError: (err, params, context) => {
      // Rollback to the previous value on error
      if (context?.previousLabels) {
        queryClient.setQueryData<MlDocumentLabel[]>([
          'ml-labels', 'documents', params.documentPartId
        ], context.previousLabels);
      }
    },
    onSettled: (data, error, params) => {
      // Invalidate the query to refetch fresh data
      queryClient.invalidateQueries({
        queryKey: ['ml-labels', 'documents', params.documentPartId],
      });
    },
  });
}
