'use client';

import { useState, useEffect } from 'react';
import { Plus, X, Check, ChevronDown, Type, ToggleLeft, Hash, ListChecks } from 'lucide-react';
import { useLabelDefinitions, useDocumentLabels, useAssignLabel, useRemoveLabelAssignment } from '@/hooks/useMlLabels';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import type { MlLabelDefinition, MlDocumentLabel } from '@/lib/types';
import { cn } from '@/lib/cn';

interface DocumentLabelAssignerProps {
  documentPartId: string;
}

// Icon for each value type
function ValueTypeIcon({ valueType }: { valueType: string }) {
  const icons: Record<string, React.ReactNode> = {
    select: <ListChecks size={14} />,
    multiselect: <ListChecks size={14} />,
    text: <Type size={14} />,
    boolean: <ToggleLeft size={14} />,
    number: <Hash size={14} />,
  };
  return <span className="text-text-tertiary">{icons[valueType] || <span />}</span>;
}

// Label value display
function LabelValueDisplay({ 
  label, 
  definition 
}: { 
  label: MlDocumentLabel; 
  definition: MlLabelDefinition 
}) {
  const getDisplayValue = () => {
    if (label.option_id && (definition.value_type === 'select' || definition.value_type === 'multiselect')) {
      return label.option_display_name || label.option_value || label.option_id;
    }
    if (label.text_value) return label.text_value;
    if (label.number_value !== null && label.number_value !== undefined) return label.number_value;
    if (label.bool_value !== null && label.bool_value !== undefined) return label.bool_value ? 'Yes' : 'No';
    return '—';
  };
  
  return (
    <Badge className="flex items-center gap-1.5 text-[12px]" variant="neutral">
      {definition.color && (
        <span 
          className="h-2 w-2 rounded-full"
          style={{ backgroundColor: definition.color }}
        />
      )}
      <ValueTypeIcon valueType={definition.value_type} />
      <span className="font-medium">{definition.name}: {getDisplayValue()}</span>
      {label.label_source === 'model' && label.confidence !== null && label.confidence !== undefined && (
        <span className="text-[10px] text-text-tertiary">({Math.round(label.confidence * 100)}%)</span>
      )}
    </Badge>
  );
}

// Boolean label editor
function BooleanLabelEditor({ 
  definition, 
  currentLabel,
  onAssign,
  onRemove 
}: { 
  definition: MlLabelDefinition;
  currentLabel: MlDocumentLabel | null;
  onAssign: (value: boolean) => void;
  onRemove: () => void;
}) {
  return (
    <div className="flex items-center gap-2">
      <button
        onClick={() => onAssign(true)}
        className={cn(
          'px-3 py-1 rounded-lg border border-border text-[12px] font-medium transition-colors',
          currentLabel?.bool_value === true 
            ? 'bg-accent-primary/10 text-accent-primary border-accent-primary' 
            : 'text-text-secondary hover:bg-bg-hover'
        )}
      >
        Yes
      </button>
      <button
        onClick={() => onAssign(false)}
        className={cn(
          'px-3 py-1 rounded-lg border border-border text-[12px] font-medium transition-colors',
          currentLabel?.bool_value === false 
            ? 'bg-accent-primary/10 text-accent-primary border-accent-primary' 
            : 'text-text-secondary hover:bg-bg-hover'
        )}
      >
        No
      </button>
      {currentLabel && (
        <Button 
          variant="ghost" 
          size="icon"
          onClick={onRemove}
          className="text-text-secondary hover:text-red-500"
        >
          <X size={14} />
        </Button>
      )}
    </div>
  );
}

// Text label editor
function TextLabelEditor({ 
  definition, 
  currentLabel,
  onAssign,
  onRemove 
}: { 
  definition: MlLabelDefinition;
  currentLabel: MlDocumentLabel | null;
  onAssign: (value: string) => void;
  onRemove: () => void;
}) {
  const [inputValue, setInputValue] = useState(currentLabel?.text_value || '');
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim()) {
      onAssign(inputValue);
    }
  };
  
  const handleClear = () => {
    setInputValue('');
    if (currentLabel) {
      onRemove();
    }
  };
  
  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2">
      <input
        type="text"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        placeholder={`Enter ${definition.name.toLowerCase()}...`}
        className={cn(
          'flex-1 rounded-lg border border-border bg-bg-secondary px-2 py-1.5 text-[13px]',
          'placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent-primary'
        )}
      />
      {inputValue ? (
        <>
          <Button type="submit" size="sm" disabled={!inputValue.trim()}>
            <Check size={14} />
          </Button>
          <Button type="button" variant="ghost" size="sm" onClick={handleClear}>
            <X size={14} />
          </Button>
        </>
      ) : null}
    </form>
  );
}

// Number label editor
function NumberLabelEditor({ 
  definition, 
  currentLabel,
  onAssign,
  onRemove 
}: { 
  definition: MlLabelDefinition;
  currentLabel: MlDocumentLabel | null;
  onAssign: (value: number) => void;
  onRemove: () => void;
}) {
  const [inputValue, setInputValue] = useState<string>(currentLabel?.number_value?.toString() || '');
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const numValue = parseFloat(inputValue);
    if (!isNaN(numValue)) {
      onAssign(numValue);
    }
  };
  
  const handleClear = () => {
    setInputValue('');
    if (currentLabel) {
      onRemove();
    }
  };
  
  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2">
      <input
        type="number"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        placeholder={`Enter ${definition.name.toLowerCase()}...`}
        className={cn(
          'flex-1 rounded-lg border border-border bg-bg-secondary px-2 py-1.5 text-[13px]',
          'placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent-primary'
        )}
      />
      {inputValue ? (
        <>
          <Button type="submit" size="sm" disabled={isNaN(parseFloat(inputValue))}>
            <Check size={14} />
          </Button>
          <Button type="button" variant="ghost" size="sm" onClick={handleClear}>
            <X size={14} />
          </Button>
        </>
      ) : null}
    </form>
  );
}

// Select label editor
interface SelectLabelEditorProps {
  definition: MlLabelDefinition;
  currentLabel: MlDocumentLabel | null;
  options: { id: string; value: string; display_name: string; color?: string | null; }[];
  onAssign: (optionId: string) => void;
  onRemove: () => void;
}

function SelectLabelEditor({ 
  definition, 
  currentLabel,
  options,
  onAssign,
  onRemove 
}: SelectLabelEditorProps) {
  const [isOpen, setIsOpen] = useState(false);
  
  const selectedOption = options.find(o => o.id === currentLabel?.option_id);
  
  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'w-full flex items-center justify-between rounded-lg border border-border bg-bg-secondary px-3 py-2 text-left',
          'text-[13px] text-text-primary hover:bg-bg-hover transition-colors'
        )}
      >
        <span className={cn(selectedOption ? 'text-text-primary' : 'text-text-tertiary')}>
          {selectedOption ? selectedOption.display_name : `Select ${definition.name}...`}
        </span>
        <ChevronDown size={14} className="text-text-tertiary" />
      </button>
      
      {isOpen && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />
          <div className="absolute top-full left-0 right-0 z-20 mt-1 rounded-lg border border-border bg-bg-secondary shadow-lg max-h-60 overflow-y-auto">
            {options.length === 0 ? (
              <div className="px-3 py-2 text-[12px] text-text-tertiary">
                No options defined
              </div>
            ) : (
              options.map((option) => (
                <button
                  key={option.id}
                  onClick={() => {
                    onAssign(option.id);
                    setIsOpen(false);
                  }}
                  className={cn(
                    'w-full px-3 py-2 text-left text-[13px] hover:bg-bg-hover transition-colors',
                    'flex items-center gap-2',
                    selectedOption?.id === option.id ? 'bg-accent-primary/10 text-accent-primary' : 'text-text-primary'
                  )}
                >
                  {option.color && (
                    <span 
                      className="h-3 w-3 rounded-full flex-shrink-0"
                      style={{ backgroundColor: option.color }}
                    />
                  )}
                  <span>{option.display_name}</span>
                  <span className="text-text-tertiary text-[11px]">({option.value})</span>
                </button>
              ))
            )}
          </div>
        </>
      )}
      
      {currentLabel && (
        <Button 
          variant="ghost" 
          size="icon"
          onClick={(e) => { e.stopPropagation(); onRemove(); }}
          className="absolute top-1 right-1 text-text-secondary hover:text-red-500"
        >
          <X size={14} />
        </Button>
      )}
    </div>
  );
}

// Multiselect label editor - simplified for now (single select to avoid complexity)
function MultiselectLabelEditor({ 
  definition, 
  currentLabels,
  options,
  onAssign,
  onRemove 
}: { 
  definition: MlLabelDefinition;
  currentLabels: MlDocumentLabel[];
  options: { id: string; value: string; display_name: string; color?: string | null; }[];
  onAssign: (optionId: string) => void;
  onRemove: (assignmentId: string) => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const selectedOptionIds = currentLabels.map(l => l.option_id).filter(Boolean) as string[];
  
  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'w-full flex items-center justify-between rounded-lg border border-border bg-bg-secondary px-3 py-2 text-left',
          'text-[13px] text-text-primary hover:bg-bg-hover transition-colors'
        )}
      >
        <span className={cn(selectedOptionIds.length > 0 ? 'text-text-primary' : 'text-text-tertiary')}>
          {selectedOptionIds.length > 0 
            ? `${selectedOptionIds.length} selected` 
            : `Select ${definition.name}...`}
        </span>
        <ChevronDown size={14} className="text-text-tertiary" />
      </button>
      
      {isOpen && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />
          <div className="absolute top-full left-0 right-0 z-20 mt-1 rounded-lg border border-border bg-bg-secondary shadow-lg max-h-60 overflow-y-auto">
            {options.length === 0 ? (
              <div className="px-3 py-2 text-[12px] text-text-tertiary">
                No options defined
              </div>
            ) : (
              options.map((option) => {
                const isSelected = selectedOptionIds.includes(option.id);
                const label = currentLabels.find(l => l.option_id === option.id);
                return (
                  <button
                    key={option.id}
                    onClick={() => {
                      if (isSelected && label) {
                        onRemove(label.id);
                      } else {
                        onAssign(option.id);
                      }
                      setIsOpen(false);
                    }}
                    className={cn(
                      'w-full px-3 py-2 text-left text-[13px] hover:bg-bg-hover transition-colors',
                      'flex items-center justify-between',
                      isSelected ? 'bg-accent-primary/10 text-accent-primary' : 'text-text-primary'
                    )}
                  >
                    <div className="flex items-center gap-2">
                      {option.color && (
                        <span 
                          className="h-3 w-3 rounded-full flex-shrink-0"
                          style={{ backgroundColor: option.color }}
                        />
                      )}
                      <span>{option.display_name}</span>
                      <span className="text-text-tertiary text-[11px]">({option.value})</span>
                    </div>
                    {isSelected && <Check size={14} />}
                  </button>
                );
              })
            )}
          </div>
        </>
      )}
    </div>
  );
}

// Render label editor based on definition type
function LabelEditor({ 
  definition, 
  currentLabel,
  currentLabels,
  options,
  onAssign,
  onRemove 
}: { 
  definition: MlLabelDefinition;
  currentLabel: MlDocumentLabel | null;
  currentLabels: MlDocumentLabel[];
  options: { id: string; value: string; display_name: string; color?: string | null; }[];
  onAssign: (value: any, isMultiselect?: boolean) => void;
  onRemove: (assignmentId?: string) => void;
}) {
  switch (definition.value_type) {
    case 'boolean':
      return (
        <BooleanLabelEditor
          definition={definition}
          currentLabel={currentLabel}
          onAssign={(value) => onAssign(value)}
          onRemove={() => onRemove(currentLabel?.id)}
        />
      );
    case 'text':
      return (
        <TextLabelEditor
          definition={definition}
          currentLabel={currentLabel}
          onAssign={(value) => onAssign(value)}
          onRemove={() => onRemove(currentLabel?.id)}
        />
      );
    case 'number':
      return (
        <NumberLabelEditor
          definition={definition}
          currentLabel={currentLabel}
          onAssign={(value) => onAssign(value)}
          onRemove={() => onRemove(currentLabel?.id)}
        />
      );
    case 'multiselect':
      return (
        <MultiselectLabelEditor
          definition={definition}
          currentLabels={currentLabels}
          options={options}
          onAssign={(optionId) => onAssign(optionId, true)}
          onRemove={(assignmentId) => onRemove(assignmentId)}
        />
      );
    case 'select':
    default:
      return (
        <SelectLabelEditor
          definition={definition}
          currentLabel={currentLabel}
          options={options}
          onAssign={(optionId) => onAssign(optionId)}
          onRemove={() => onRemove(currentLabel?.id)}
        />
      );
  }
}

export function DocumentLabelAssigner({ documentPartId }: DocumentLabelAssignerProps) {
  const [expanded, setExpanded] = useState(false);
  
  const { data: definitions, isLoading: isLoadingDefinitions } = useLabelDefinitions(true);
  const { data: labels, isLoading: isLoadingLabels } = useDocumentLabels(documentPartId);
  const assignLabelMutation = useAssignLabel();
  const removeLabelMutation = useRemoveLabelAssignment();
  
  // Get options for each definition
  const [optionsMap, setOptionsMap] = useState<Record<string, any[]>>({});
  
  // Group labels by definition
  const labelsByDefinition: Record<string, MlDocumentLabel[]> = {};
  if (labels) {
    for (const label of labels) {
      const defId = label.definition_id;
      labelsByDefinition[defId] = labelsByDefinition[defId] || [];
      labelsByDefinition[defId].push(label);
    }
  }
  
  // Handle assigning a label
  const handleAssignLabel = (definition: MlLabelDefinition, value: any, isMultiselect?: boolean) => {
    assignLabelMutation.mutate({
      documentPartId,
      definitionId: definition.id,
      optionId: typeof value === 'string' ? value : undefined,
      textValue: typeof value === 'string' && definition.value_type === 'text' ? value : undefined,
      numberValue: typeof value === 'number' ? value : undefined,
      boolValue: typeof value === 'boolean' ? value : undefined,
      labelSource: 'human',
    });
  };
  
  // Handle removing a label
  const handleRemoveLabel = (assignmentId?: string) => {
    if (assignmentId) {
      // We need to extract document_part_id from the assignment
      // For now, we'll use the provided documentPartId
      removeLabelMutation.mutate({
        documentPartId,
        assignmentId,
      });
    }
  };
  
  // Check if any labels exist
  const hasLabels = labels && labels.length > 0;
  const hasDefinitions = definitions && definitions.length > 0;
  
  if (!hasDefinitions && !isLoadingDefinitions) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center">
        <p className="text-[14px] text-text-secondary">
          No label dimensions defined yet
        </p>
        <a 
          href="/labels" 
          className="mt-2 text-[14px] text-accent-primary hover:underline"
        >
          Create one in the Labels tab
        </a>
      </div>
    );
  }
  
  return (
    <div className="space-y-3">
      {/* Current labels display */}
      {hasLabels && expanded && (
        <div className="flex flex-wrap gap-2 pb-2">
          {labels?.map((label) => {
            const definition = definitions?.find(d => d.id === label.definition_id);
            if (!definition) return null;
            return (
              <LabelValueDisplay 
                key={label.id} 
                label={label} 
                definition={definition} 
              />
            );
          })}
        </div>
      )}
      
      {/* Label editors */}
      <div className={cn(
        'grid gap-3',
        expanded ? 'grid-cols-1' : 'grid-cols-1'
      )}>
        {definitions?.map((definition) => {
          const currentLabelsForDef = labelsByDefinition[definition.id] || [];
          const currentLabel = currentLabelsForDef[0] || null;
          
          return (
            <div 
              key={definition.id} 
              className="rounded-lg border border-border bg-bg-secondary p-3"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  {definition.color && (
                    <span 
                      className="h-3 w-3 rounded-full"
                      style={{ backgroundColor: definition.color }}
                    />
                  )}
                  <ValueTypeIcon valueType={definition.value_type} />
                  <span className="text-[13px] font-medium text-text-primary">{definition.name}</span>
                </div>
              </div>
              
              <LabelEditor
                definition={definition}
                currentLabel={currentLabel}
                currentLabels={currentLabelsForDef}
                options={[]} // Options will be loaded separately if needed
                onAssign={(value, isMultiselect) => handleAssignLabel(definition, value, isMultiselect)}
                onRemove={(assignmentId) => handleRemoveLabel(assignmentId)}
              />
            </div>
          );
        })}
      </div>
      
      {/* Expand/collapse toggle */}
      {hasLabels && (
        <Button 
          variant="ghost" 
          size="sm"
          onClick={() => setExpanded(!expanded)}
          className="w-full mt-2"
        >
          {expanded ? 'Hide current labels' : `Show ${labels?.length || 0} assigned label${(labels?.length || 0) !== 1 ? 's' : ''}`}
        </Button>
      )}
    </div>
  );
}
