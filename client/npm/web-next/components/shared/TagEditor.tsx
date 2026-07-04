'use client';

import { useState, useEffect } from 'react';
import { Plus, X, Loader2 } from 'lucide-react';
import { useAvailableTags, useDocumentTags, useAddTag, useRemoveTag, useCreateTag } from '@/hooks/usePaperlessTags';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/cn';
import type { PaperlessTag } from '@/lib/types';

import React from 'react';

/**
 * TagEditor component for Paperless document tag management.
 * 
 * Features:
 * - Display current tags as removable chips
 * - "+ Add tag" action
 * - Searchable combobox
 * - Autocomplete from useAvailableTags
 * - Create new tag on-the-fly when no match is found
 * - Only renders for Paperless documents (source_type === "paperless")
 */

// Minimal document type for TagEditor
interface TagEditorDocument {
  document_part_id: string;
  source_type: string;
  scope_json?: string;
}

interface TagEditorProps {
  documentPart: TagEditorDocument | null;
  connectionId: string | null;
  onTagChange?: () => void; // Optional callback when tags change
}

export function TagEditor({ documentPart, connectionId, onTagChange }: TagEditorProps) {
  // Only render if this is a Paperless document
  if (documentPart?.source_type !== 'paperless' || !connectionId) {
    return null;
  }

  const [isAddingTag, setIsAddingTag] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTagIndex, setSelectedTagIndex] = useState(0);
  const [creatingNewTag, setCreatingNewTag] = useState(false);
  
  // Query current document tags
  const { data: documentTags, isLoading: isLoadingDocumentTags } = useDocumentTags(documentPart.document_part_id);
  
  // Query available tags for autocomplete
  const { data: availableTags, isLoading: isLoadingAvailableTags } = useAvailableTags(connectionId);
  
  // Mutation hooks
  const { mutate: addTagMutation, isPending: isAdding } = useAddTag();
  const { mutate: removeTagMutation, isPending: isRemoving } = useRemoveTag();
  const { mutate: createTagMutation, isPending: isCreating } = useCreateTag();

  // Available tags from API response
  const availableTagsList: PaperlessTag[] = availableTags?.tags || [];
  
  // Filter tags based on search query
  const filteredTags: PaperlessTag[] = availableTagsList.filter(tag => 
    tag.name.toLowerCase().includes(searchQuery.toLowerCase())
  );
  
  // Show "Create new tag" option when there's a search query but no matches
  const showCreateOption = searchQuery.length > 0 && filteredTags.length === 0 && !isLoadingAvailableTags;
  
  // Reset state when component unmounts or props change
  useEffect(() => {
    setIsAddingTag(false);
    setSearchQuery('');
    setSelectedTagIndex(0);
    setCreatingNewTag(false);
  }, [documentPart?.document_part_id, connectionId]);

  // Handle adding a tag
  const handleAddTag = (tag: PaperlessTag) => {
    addTagMutation(
      { documentPartId: documentPart.document_part_id, tagId: tag.id },
      {
        onSuccess: () => {
          setIsAddingTag(false);
          setSearchQuery('');
          setSelectedTagIndex(0);
          onTagChange?.();
        },
        onError: (error) => {
          console.error('Failed to add tag:', error);
          // Error is already handled in the mutation
        }
      }
    );
  };

  // Handle creating and adding a new tag
  const handleCreateAndAddTag = () => {
    if (!searchQuery.trim() || !connectionId) return;
    
    createTagMutation(
      { connectionId, name: searchQuery.trim() },
      {
        onSuccess: (newTag) => {
          // Immediately add the newly created tag to the document
          addTagMutation(
            { documentPartId: documentPart.document_part_id, tagId: newTag.id },
            {
              onSuccess: () => {
                setIsAddingTag(false);
                setSearchQuery('');
                setSelectedTagIndex(0);
                setCreatingNewTag(false);
                onTagChange?.();
              },
              onError: (error) => {
                console.error('Failed to add newly created tag:', error);
              }
            }
          );
        },
        onError: (error) => {
          console.error('Failed to create tag:', error);
        }
      }
    );
  };

  // Handle removing a tag
  const handleRemoveTag = (tagId: number, event: React.MouseEvent) => {
    event.stopPropagation(); // Prevent triggering tag selection
    
    removeTagMutation(
      { documentPartId: documentPart.document_part_id, tagId },
      {
        onSuccess: () => {
          onTagChange?.();
        },
        onError: (error) => {
          console.error('Failed to remove tag:', error);
        }
      }
    );
  };

  // Handle keyboard navigation in the dropdown
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isAddingTag) return;
    
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedTagIndex(prev => {
          const maxIndex = showCreateOption ? filteredTags.length : filteredTags.length - 1;
          return Math.min(prev + 1, maxIndex);
        });
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedTagIndex(prev => Math.max(prev - 1, 0));
        break;
      case 'Enter':
        e.preventDefault();
        if (filteredTags.length > 0 && selectedTagIndex >= 0 && selectedTagIndex < filteredTags.length) {
          handleAddTag(filteredTags[selectedTagIndex]!);
        } else if (showCreateOption) {
          handleCreateAndAddTag();
        }
        break;
      case 'Escape':
        e.preventDefault();
        setIsAddingTag(false);
        setSearchQuery('');
        setSelectedTagIndex(0);
        break;
      default:
        // Reset selected index when typing
        if (e.key.length === 1 || e.key === 'Backspace') {
          setSelectedTagIndex(0);
        }
        break;
    }
  };

  // Current tags from document
  const currentTags: PaperlessTag[] = documentTags?.tags || [];
  const currentTagIds: number[] = documentTags?.tag_ids || [];

  return (
    <div className="flex flex-wrap items-center gap-2">
      {/* Current tags as removable chips */}
      {isLoadingDocumentTags ? (
        <Badge variant="neutral">
          <Loader2 className="h-3 w-3 animate-spin" />
        </Badge>
      ) : currentTags.length === 0 ? (
        <span className="text-[12px] text-text-tertiary">No tags</span>
      ) : (
        currentTags.map(tag => (
          <Badge 
            key={tag.id} 
            variant="neutral"
            className="flex items-center gap-1 cursor-pointer hover:bg-bg-hover transition-colors"
            onClick={() => {}}
          >
            {tag.name}
            <button
              onClick={(e) => handleRemoveTag(tag.id, e)}
              className="ml-1 rounded-full p-0.5 hover:bg-bg-tertiary transition-colors disabled:opacity-50"
              disabled={isRemoving}
              title="Remove tag"
            >
              <X className="h-2.5 w-2.5" />
            </button>
          </Badge>
        ))
      )}

      {/* Add tag button */}
      {!isAddingTag ? (
        <Button
          size="sm"
          variant="ghost"
          onClick={() => {
            setIsAddingTag(true);
            setSearchQuery('');
            setSelectedTagIndex(0);
          }}
          className="h-6 px-2 text-xs font-normal"
        >
          <Plus className="h-3 w-3" />
          <span>Add tag</span>
        </Button>
      ) : (
        <div className="relative">
          {/* Search input */}
          <div className="flex items-center gap-1">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setSelectedTagIndex(0);
              }}
              onKeyDown={handleKeyDown}
              onFocus={() => {}}
              placeholder="Search or create tag..."
              className={cn(
                'h-6 w-48 rounded-md border border-border bg-bg-secondary px-2 text-xs',
                'focus:outline-none focus:ring-1 focus:ring-accent-primary focus:border-transparent',
                'placeholder:text-text-tertiary'
              )}
              autoFocus
            />
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setIsAddingTag(false);
                setSearchQuery('');
              }}
              className="h-6 w-6 p-0"
              title="Cancel"
            >
              <X className="h-3 w-3" />
            </Button>
          </div>

          {/* Dropdown with filtered tags */}
          {isAddingTag && (isLoadingAvailableTags ? filteredTags.length > 0 : true) && (
            <div className="absolute left-0 right-0 mt-1 z-50 rounded-md border border-border bg-bg-secondary shadow-lg overflow-hidden">
              {isLoadingAvailableTags ? (
                <div className="flex items-center justify-center py-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                </div>
              ) : filteredTags.length > 0 ? (
                <div className="max-h-60 overflow-y-auto">
                  {filteredTags.map((tag, index) => (
                    <button
                      key={tag.id}
                      onClick={() => handleAddTag(tag)}
                      onMouseEnter={() => setSelectedTagIndex(index)}
                      className={cn(
                        'w-full px-3 py-2 text-left text-xs transition-colors',
                        'hover:bg-bg-hover flex items-center justify-between',
                        index === selectedTagIndex ? 'bg-bg-hover' : '',
                        currentTagIds.includes(tag.id) ? 'opacity-50 cursor-not-allowed' : ''
                      )}
                      disabled={currentTagIds.includes(tag.id)}
                    >
                      <span>{tag.name}</span>
                      {tag.color && (
                        <span 
                          className="h-2 w-2 rounded-full" 
                          style={{ backgroundColor: tag.color }}
                        />
                      )}
                    </button>
                  ))}
                </div>
              ) : showCreateOption && (
                <button
                  onClick={handleCreateAndAddTag}
                  className={cn(
                    'w-full px-3 py-2 text-left text-xs transition-colors flex items-center gap-2',
                    'hover:bg-bg-hover text-accent-primary'
                  )}
                  disabled={isCreating || isAdding}
                >
                  <Plus className="h-3 w-3" />
                  <span>Create "{searchQuery}"</span>
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* Loading indicators */}
      {(isAdding || isRemoving || isCreating) && (
        <Loader2 className="h-3 w-3 animate-spin text-text-tertiary" />
      )}
    </div>
  );
}

// Memoized component to prevent unnecessary re-renders
export const MemoizedTagEditor = React.memo(TagEditor);