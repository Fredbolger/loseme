'use client';

import { useState, useEffect, memo } from 'react';
import { Settings, X, Loader2, Check, ChevronDown, Plus } from 'lucide-react';
import {
  useAvailableTagsForSource,
  useAvailableCorrespondents,
  useAvailableDocumentTypes,
  useUpdateSourceScope,
  extractConnectionIdFromSource,
} from '@/hooks/usePaperlessSourceScope';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { cn } from '@/lib/cn';
import type { MonitoredSource, PaperlessSourceScope } from '@/lib/types';

/**
 * SourceScopeEditor component for editing Paperless source indexing filters.
 * 
 * Features:
 * - Display current indexing scope (tags, correspondents, document types)
 * - Searchable dropdowns for each filter type
 * - Multi-select capability
 * - Clear/reset filters
 * - Save changes to backend
 */

interface SourceScopeEditorProps {
  source: MonitoredSource | null;
  onClose: () => void;
  onSuccess?: () => void;
}

// Filter type for the selector
type FilterType = 'tags' | 'correspondents' | 'document_types';

// Item types for the different filter categories
interface FilterItem {
  id: number;
  name: string;
  color?: string | null;
}

const FILTER_LABELS: Record<FilterType, string> = {
  tags: 'Tags',
  correspondents: 'Correspondents',
  document_types: 'Document Types',
};

const FILTER_DESCRIPTIONS: Record<FilterType, string> = {
  tags: 'Filter documents by tag',
  correspondents: 'Filter documents by correspondent',
  document_types: 'Filter documents by document type',
};

export function SourceScopeEditor({ source, onClose, onSuccess }: SourceScopeEditorProps) {
  const connectionId = extractConnectionIdFromSource(source);
  
  // Fetch available items for each filter type
  const { data: availableTagsData, isLoading: isLoadingTags } = useAvailableTagsForSource(connectionId);
  const { data: availableCorrespondentsData, isLoading: isLoadingCorrespondents } = useAvailableCorrespondents(connectionId);
  const { data: availableDocumentTypesData, isLoading: isLoadingDocumentTypes } = useAvailableDocumentTypes(connectionId);
  
  // Update source scope mutation
  const { mutate: updateScope, isPending: isUpdating } = useUpdateSourceScope();
  
  // State for the current scope
  const [currentScope, setCurrentScope] = useState<PaperlessSourceScope>({
    tag_ids: null,
    correspondent_ids: null,
    document_type_ids: null,
  });
  
  // State for the dropdown
  const [isOpen, setIsOpen] = useState(false);
  const [activeFilterType, setActiveFilterType] = useState<FilterType | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedIndices, setSelectedIndices] = useState<number[]>([]);
  
  // Parse the current scope from the source
  useEffect(() => {
    if (!source || source.source_type !== 'paperless') {
      setCurrentScope({
        tag_ids: null,
        correspondent_ids: null,
        document_type_ids: null,
      });
      return;
    }
    
    const scopeData = source.scope;
    
    if (!scopeData) {
      setCurrentScope({
        tag_ids: null,
        correspondent_ids: null,
        document_type_ids: null,
      });
      return;
    }
    
    // Handle different scope formats
    let parsedScope: any = null;
    
    if (typeof scopeData === 'string') {
      try {
        parsedScope = JSON.parse(scopeData);
      } catch {
        parsedScope = {};
      }
    } else if (typeof scopeData === 'object' && scopeData !== null) {
      parsedScope = scopeData;
    }
    
    setCurrentScope({
      tag_ids: parsedScope?.tag_ids || null,
      correspondent_ids: parsedScope?.correspondent_ids || null,
      document_type_ids: parsedScope?.document_type_ids || null,
    });
  }, [source]);
  
  // Get the currently selected items for a filter type
  const getSelectedIds = (filterType: FilterType): number[] => {
    switch (filterType) {
      case 'tags':
        return currentScope.tag_ids || [];
      case 'correspondents':
        return currentScope.correspondent_ids || [];
      case 'document_types':
        return currentScope.document_type_ids || [];
      default:
        return [];
    }
  };
  
  const getSelectedItems = (filterType: FilterType): FilterItem[] => {
    const availableItems = getAvailableItems(filterType);
    const selectedIds = getSelectedIds(filterType);
    
    return availableItems.filter(item => selectedIds.includes(item.id));
  };
  
  // Get all available items for a filter type
  const getAvailableItems = (filterType: FilterType): FilterItem[] => {
    switch (filterType) {
      case 'tags':
        return availableTagsData?.tags.map(t => ({ id: t.id, name: t.name, color: t.color })) || [];
      case 'correspondents':
        return availableCorrespondentsData?.correspondents.map(c => ({ id: c.id, name: c.name })) || [];
      case 'document_types':
        return availableDocumentTypesData?.document_types.map(dt => ({ id: dt.id, name: dt.name })) || [];
      default:
        return [];
    }
  };
  
  // Filter items based on search query
  const filteredItems = (filterType: FilterType): FilterItem[] => {
    const items = getAvailableItems(filterType);
    const selectedIds = getSelectedIds(filterType);
    
    return items.filter(item => 
      item.name.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !selectedIds.includes(item.id)
    );
  };
  
  // Open dropdown for a specific filter type
  const openDropdown = (filterType: FilterType) => {
    setActiveFilterType(filterType);
    setSearchQuery('');
    setSelectedIndices([]);
    setIsOpen(true);
  };
  
  // Close the dropdown
  const closeDropdown = () => {
    setIsOpen(false);
    setActiveFilterType(null);
    setSearchQuery('');
    setSelectedIndices([]);
  };
  
  // Toggle a filter item
  const toggleFilterItem = (filterType: FilterType, itemId: number) => {
    const currentIds = getSelectedIds(filterType);
    const newIds = currentIds.includes(itemId)
      ? currentIds.filter(id => id !== itemId)
      : [...currentIds, itemId];
    
    setCurrentScope({
      ...currentScope,
      [filterType + '_ids']: newIds.length > 0 ? newIds : null,
    });
  };
  
  // Add an item from the dropdown
  const addItemFromDropdown = (item: FilterItem) => {
    if (!activeFilterType) return;
    
    toggleFilterItem(activeFilterType, item.id);
    // Keep the dropdown open for multi-select
    // Don't close it automatically
  };
  
  // Remove a selected item
  const removeItem = (filterType: FilterType, itemId: number) => {
    toggleFilterItem(filterType, itemId);
  };
  
  // Check if all items are selected
  const allItemsSelected = (filterType: FilterType): boolean => {
    const availableItems = getAvailableItems(filterType);
    const selectedIds = getSelectedIds(filterType);
    
    if (availableItems.length === 0) return false;
    
    return availableItems.every(item => selectedIds.includes(item.id));
  };
  
  // Toggle all items for a filter type
  const toggleAllItems = (filterType: FilterType) => {
    const availableItems = getAvailableItems(filterType);
    
    if (allItemsSelected(filterType)) {
      // Deselect all
      setCurrentScope({
        ...currentScope,
        [filterType + '_ids']: null,
      });
    } else {
      // Select all
      setCurrentScope({
        ...currentScope,
        [filterType + '_ids']: availableItems.map(item => item.id),
      });
    }
  };
  
  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen || !activeFilterType) return;
    
    const filtered = filteredItems(activeFilterType);
    
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndices((prev) => {
          const lastIndex = filtered.length - 1;
          if (prev.length === 0 || prev[0] === undefined) return [0];
          return [Math.min(prev[0] + 1, lastIndex)];
        });
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndices((prev) => {
          if (prev.length === 0 || prev[0] === undefined) return [0];
          return [Math.max(prev[0] - 1, 0)];
        });
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedIndices.length > 0 && selectedIndices[0] !== undefined && selectedIndices[0] >= 0 && selectedIndices[0] < filtered.length) {
          const selectedItem = filtered[selectedIndices[0]];
          if (selectedItem) {
            addItemFromDropdown(selectedItem);
          }
        }
        break;
      case 'Escape':
        e.preventDefault();
        closeDropdown();
        break;
      default:
        // Reset selected index when typing
        if (e.key.length === 1 || e.key === 'Backspace') {
          setSelectedIndices([]);
        }
        break;
    }
  };
  
  // Save the scope configuration
  const handleSave = () => {
    if (!source) return;
    
    updateScope(
      {
        sourceId: source.id,
        scope: currentScope,
      },
      {
        onSuccess: () => {
          onSuccess?.();
          onClose();
        },
      }
    );
  };
  
  // Reset to no filters (index nothing)
  const handleResetAll = () => {
    setCurrentScope({
      tag_ids: null,
      correspondent_ids: null,
      document_type_ids: null,
    });
  };
  
  // Check if any filters are active
  const hasActiveFilters = 
    (currentScope.tag_ids && currentScope.tag_ids.length > 0) ||
    (currentScope.correspondent_ids && currentScope.correspondent_ids.length > 0) ||
    (currentScope.document_type_ids && currentScope.document_type_ids.length > 0);
  
  // Check if there are unsaved changes compared to the source
  const hasChanges = () => {
    if (!source || source.source_type !== 'paperless') return false;
    
    const scopeData = source.scope;
    if (!scopeData) return hasActiveFilters;
    
    let originalScope: any = {};
    
    if (typeof scopeData === 'string') {
      try {
        originalScope = JSON.parse(scopeData);
      } catch {
        originalScope = {};
      }
    } else if (typeof scopeData === 'object' && scopeData !== null) {
      originalScope = scopeData;
    }
    
    return (
      JSON.stringify(currentScope.tag_ids || []) !== JSON.stringify(originalScope.tag_ids || []) ||
      JSON.stringify(currentScope.correspondent_ids || []) !== JSON.stringify(originalScope.correspondent_ids || []) ||
      JSON.stringify(currentScope.document_type_ids || []) !== JSON.stringify(originalScope.document_type_ids || [])
    );
  };
  
  // Loading state
  if (!source || source.source_type !== 'paperless') {
    return (
      <div className="flex flex-col gap-4 p-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">Edit Source Scope</h3>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        <p className="text-text-tertiary">This is not a Paperless source.</p>
      </div>
    );
  }
  
  const isLoading = isLoadingTags || isLoadingCorrespondents || isLoadingDocumentTypes;
  
  return (
    <div className="flex flex-col gap-4 p-4 w-full max-w-md">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-text-primary">Edit Source Scope</h3>
        <Button variant="ghost" size="icon" onClick={onClose} disabled={isUpdating}>
          <X className="h-4 w-4" />
        </Button>
      </div>
      
      {/* Description */}
      <p className="text-sm text-text-tertiary">
        Configure which documents from Paperless should be indexed. Only selected items will be indexed.
      </p>
      
      {/* Loading indicator */}
      {isLoading && (
        <div className="flex items-center justify-center py-4">
          <Loader2 className="h-6 w-6 animate-spin" />
        </div>
      )}
      
      {/* Filter sections */}
      {!isLoading && (
        <div className="flex flex-col gap-4">
          {/* Tags Filter */}
          <FilterSection
            filterType="tags"
            label={FILTER_LABELS.tags}
            description={FILTER_DESCRIPTIONS.tags}
            selectedItems={getSelectedItems('tags')}
            availableCount={getAvailableItems('tags').length}
            onAdd={openDropdown}
            onRemove={(itemId) => removeItem('tags', itemId)}
            isOpen={isOpen && activeFilterType === 'tags'}
          />
          
          {/* Correspondents Filter */}
          <FilterSection
            filterType="correspondents"
            label={FILTER_LABELS.correspondents}
            description={FILTER_DESCRIPTIONS.correspondents}
            selectedItems={getSelectedItems('correspondents')}
            availableCount={getAvailableItems('correspondents').length}
            onAdd={openDropdown}
            onRemove={(itemId) => removeItem('correspondents', itemId)}
            isOpen={isOpen && activeFilterType === 'correspondents'}
          />
          
          {/* Document Types Filter */}
          <FilterSection
            filterType="document_types"
            label={FILTER_LABELS.document_types}
            description={FILTER_DESCRIPTIONS.document_types}
            selectedItems={getSelectedItems('document_types')}
            availableCount={getAvailableItems('document_types').length}
            onAdd={openDropdown}
            onRemove={(itemId) => removeItem('document_types', itemId)}
            isOpen={isOpen && activeFilterType === 'document_types'}
          />
        </div>
      )}
      
      {/* Dropdown for selecting items */}
      {isOpen && activeFilterType && (
        <div className="relative">
          <div className="fixed inset-0 z-[60] bg-black/50 backdrop-blur-sm" onClick={closeDropdown} />
          <div className="absolute top-0 left-0 right-0 mt-1 z-[70] rounded-md border border-border bg-bg-secondary shadow-lg overflow-hidden">
            <div className="flex items-center justify-between px-3 py-2 border-b border-border">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setSelectedIndices([]);
                }}
                onKeyDown={handleKeyDown}
                placeholder={`Search ${FILTER_LABELS[activeFilterType]}...`}
                className="flex-1 bg-transparent outline-none text-sm"
                autoFocus
              />
              <Button
                variant="ghost"
                size="sm"
                onClick={() => toggleAllItems(activeFilterType)}
                className="text-xs h-6 px-2"
              >
                {allItemsSelected(activeFilterType) ? 'Clear All' : 'Select All'}
              </Button>
            </div>
            
            <div className="max-h-60 overflow-y-auto">
              {filteredItems(activeFilterType).length === 0 ? (
                <div className="px-3 py-4 text-center text-sm text-text-tertiary">
                  No {FILTER_LABELS[activeFilterType].toLowerCase()} found
                </div>
              ) : (
                filteredItems(activeFilterType).map((item, index) => (
                  <button
                    key={item.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      addItemFromDropdown(item);
                    }}
                    onMouseEnter={() => setSelectedIndices([index])}
                    className={cn(
                      'w-full px-3 py-2 text-left text-sm transition-colors',
                      'hover:bg-bg-hover flex items-center justify-between',
                      selectedIndices.includes(index) ? 'bg-bg-hover' : ''
                    )}
                  >
                    <div className="flex items-center gap-2">
                      {item.color && (
                        <span
                          className="h-2 w-2 rounded-full flex-shrink-0"
                          style={{ backgroundColor: item.color }}
                        />
                      )}
                      <span>{item.name}</span>
                    </div>
                    {getSelectedItems(activeFilterType).some(selected => selected.id === item.id) && (
                      <Check className="h-4 w-4 text-accent-primary" />
                    )}
                  </button>
                ))
              )}
            </div>
          </div>
        </div>
      )}
      
      {/* Actions */}
      <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
        <Button variant="outline" size="sm" onClick={handleResetAll} disabled={!hasActiveFilters || isUpdating}>
          Reset All
        </Button>
        <Button variant="outline" size="sm" onClick={onClose} disabled={isUpdating}>
          Cancel
        </Button>
        <Button
          size="sm"
          onClick={handleSave}
          disabled={!hasChanges() || isUpdating}
          className="gap-1"
        >
          {isUpdating ? (
            <>
              <Loader2 className="h-3 w-3 animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <Settings className="h-3 w-3" />
              Save Changes
            </>
          )}
        </Button>
      </div>
    </div>
  );
}

// Filter section component for each filter type
interface FilterSectionProps {
  filterType: FilterType;
  label: string;
  description: string;
  selectedItems: FilterItem[];
  availableCount: number;
  onAdd: (filterType: FilterType) => void;
  onRemove: (itemId: number) => void;
  isOpen: boolean;
}

function FilterSection({
  filterType,
  label,
  description,
  selectedItems,
  availableCount,
  onAdd,
  onRemove,
  isOpen,
}: FilterSectionProps) {
  const hasSelection = selectedItems.length > 0;
  
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <div>
          <label className="text-sm font-medium text-text-primary">{label}</label>
          <p className="text-xs text-text-tertiary">{description}</p>
        </div>
        <button
          onClick={() => onAdd(filterType)}
          className={cn(
            'flex items-center gap-1 px-2 py-1 rounded-md text-xs transition-colors',
            'hover:bg-bg-hover',
            isOpen ? 'bg-bg-hover' : ''
          )}
        >
          <Plus className="h-3 w-3" />
          Add
          {availableCount > 0 && (
            <Badge variant="neutral" className="h-4 px-1 text-[10px]">
              {availableCount}
            </Badge>
          )}
        </button>
      </div>
      
      {/* Selected items */}
      {hasSelection ? (
        <div className="flex flex-wrap gap-1">
          {selectedItems.map((item) => (
            <Badge
              key={item.id}
              variant="neutral"
              className="flex items-center gap-1 h-6"
            >
              {item.color && (
                <span
                  className="h-2 w-2 rounded-full"
                  style={{ backgroundColor: item.color }}
                />
              )}
              <span className="text-xs">{item.name}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onRemove(item.id);
                }}
                className="ml-1 rounded-full p-0.5 hover:bg-bg-tertiary transition-colors"
                title="Remove"
              >
                <X className="h-2.5 w-2.5" />
              </button>
            </Badge>
          ))}
        </div>
      ) : (
        <p className="text-xs text-text-tertiary">
          No {label.toLowerCase()} selected - none will be indexed
        </p>
      )}
    </div>
  );
}

export const MemoizedSourceScopeEditor = memo(SourceScopeEditor);
