'use client';

import { useState } from 'react';
import { Pencil, Trash2, Plus, X } from 'lucide-react';
import { useLabelOptions, useDeleteLabelDefinition, useDeleteLabelOption } from '@/hooks/useMlLabels';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import type { MlLabelDefinition, MlLabelOption, MlLabelStatistic } from '@/lib/types';
import { cn } from '@/lib/cn';

interface LabelDefinitionCardProps {
  definition: MlLabelDefinition;
  onEdit: (definition: MlLabelDefinition) => void;
  onAddOption: (definition: MlLabelDefinition) => void;
  onEditOption: (option: MlLabelOption) => void;
  statistics?: MlLabelStatistic[];
}

// Color swatch component
function ColorSwatch({ color }: { color?: string | null }) {
  if (!color) return null;
  return (
    <div 
      className="h-4 w-4 rounded-full border border-border"
      style={{ backgroundColor: color }}
    />
  );
}

// Value type badge
function ValueTypeBadge({ valueType }: { valueType: string }) {
  const getColor = () => {
    switch (valueType) {
      case 'select': return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300';
      case 'multiselect': return 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300';
      case 'text': return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300';
      case 'boolean': return 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300';
      case 'number': return 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-300';
      default: return 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-300';
    }
  };
  
  return (
    <Badge className={cn('text-[11px] font-medium', getColor())}>
      {valueType}
    </Badge>
  );
}

// Option chip
interface OptionChipProps {
  option: MlLabelOption;
  onEdit: () => void;
  onDelete: () => void;
}

function OptionChip({ option, onEdit, onDelete }: OptionChipProps) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  
  return (
    <>
      <div className="group flex items-center gap-2 rounded-lg border border-border bg-bg-secondary px-2 py-1 text-[12px]">
        <ColorSwatch color={option.color} />
        <span className="truncate text-text-primary">{option.display_name}</span>
        <span className="text-text-tertiary">({option.value})</span>
        <div className="opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
          <button 
            onClick={(e) => { e.stopPropagation(); onEdit(); }}
            className="text-[10px] text-text-secondary hover:text-text-primary"
          >
            <Pencil size={12} />
          </button>
          <button 
            onClick={(e) => { e.stopPropagation(); setShowDeleteConfirm(true); }}
            className="text-[10px] text-text-secondary hover:text-red-500"
          >
            <X size={12} />
          </button>
        </div>
      </div>
      
      <ConfirmDialog
        open={showDeleteConfirm}
        onOpenChange={setShowDeleteConfirm}
        title="Delete Option"
        description={`Are you sure you want to delete the option "${option.display_name}"? This cannot be undone.`}
        confirmLabel="Delete"
        cancelLabel="Cancel"
        onConfirm={onDelete}
        destructive
      />
    </>
  );
}

export function LabelDefinitionCard({ 
  definition, 
  onEdit, 
  onAddOption,
  onEditOption,
  statistics
}: LabelDefinitionCardProps) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [expanded, setExpanded] = useState(false);
  
  const { data: options, isLoading: isLoadingOptions } = useLabelOptions(definition.id);
  const deleteDefinitionMutation = useDeleteLabelDefinition();
  const deleteOptionMutation = useDeleteLabelOption();
  
  const handleDelete = () => {
    deleteDefinitionMutation.mutate(definition.id, {
      onSuccess: () => {},
      onError: (error) => {
        console.error('Failed to delete label definition:', error);
      }
    });
  };
  
  const handleDeleteOption = (optionId: string) => {
    deleteOptionMutation.mutate(optionId, {
      onSuccess: () => {},
      onError: (error) => {
        console.error('Failed to delete label option:', error);
      }
    });
  };
  
  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <ColorSwatch color={definition.color} />
            <span className="text-[15px] font-semibold text-text-primary">{definition.name}</span>
            <ValueTypeBadge valueType={definition.value_type} />
          </div>
          
          <div className="flex items-center gap-2 text-[12px]">
            <span className="font-mono text-text-tertiary">{definition.key}</span>
          </div>
          
          {definition.description && (
            <p className="mt-2 text-[13px] text-text-secondary">{definition.description}</p>
          )}
          
          {/* Statistics section */}
          {statistics?.length ? (
            <div className="mt-2 flex flex-wrap gap-2">
              {statistics.map((stat, idx) => (
                <span key={stat.option_id || stat.option_value || idx} 
                  className="flex items-center gap-1 text-[11px] font-mono text-text-tertiary"
                >
                  <span 
                    className="h-2 w-2 rounded-full"
                    style={{ backgroundColor: stat.option_color || 'transparent' }}
                  />
                  {stat.option_display_name || stat.option_value || 'N/A'}: {stat.count}
                </span>
              ))}
              <span className="text-[11px] text-text-tertiary">
                ({statistics.reduce((sum, s) => sum + s.count, 0)} total)
              </span>
            </div>
          ) : null}
          
          {/* Options section */}
          {definition.value_type === 'select' || definition.value_type === 'multiselect' ? (
            <div className="mt-3">
              <button 
                onClick={() => setExpanded(!expanded)}
                className="flex items-center gap-1 text-[12px] font-medium text-text-secondary hover:text-text-primary"
              >
                {expanded ? 'Hide options' : `Show ${options?.length || 0} option${(options?.length || 0) !== 1 ? 's' : ''}`}
                {expanded ? <X size={12} /> : <Plus size={12} />}
              </button>
              
              {expanded && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {isLoadingOptions ? (
                    <div className="text-[12px] text-text-tertiary">Loading options...</div>
                  ) : options && options.length > 0 ? (
                    options.map((option) => (
                      <OptionChip
                        key={option.id}
                        option={option}
                        onEdit={() => onEditOption(option)}
                        onDelete={() => handleDeleteOption(option.id)}
                      />
                    ))
                  ) : (
                    <div className="text-[12px] text-text-tertiary">No options defined</div>
                  )}
                  
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => onAddOption(definition)}
                    className="mt-2"
                  >
                    <Plus size={14} /> Add option
                  </Button>
                </div>
              )}
            </div>
          ) : null}
        </div>
        
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" onClick={() => onEdit(definition)}>
            <Pencil size={14} />
          </Button>
          <Button 
            variant="ghost" 
            size="icon" 
            onClick={() => setShowDeleteConfirm(true)}
            className="text-text-secondary hover:text-red-500"
          >
            <Trash2 size={14} />
          </Button>
        </div>
      </div>
      
      <ConfirmDialog
        open={showDeleteConfirm}
        onOpenChange={setShowDeleteConfirm}
        title="Delete Label Definition"
        description={`Are you sure you want to delete "${definition.name}"? This will also delete all options and label assignments for this definition. This cannot be undone.`}
        confirmLabel="Delete"
        cancelLabel="Cancel"
        onConfirm={handleDelete}
        destructive
      />
    </Card>
  );
}
