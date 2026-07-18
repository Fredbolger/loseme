'use client';

import { useState, useEffect } from 'react';
import { X, Plus } from 'lucide-react';
import { useCreateLabelDefinition, useUpdateLabelDefinition, useCreateLabelOption } from '@/hooks/useMlLabels';
import { Button } from '@/components/ui/Button';
import type { MlLabelDefinition, MlLabelOption } from '@/lib/types';
import type { LabelValueType } from '@/lib/types';
import { cn } from '@/lib/cn';

interface LabelDefinitionFormProps {
  definition?: MlLabelDefinition | null;
  onClose: () => void;
  onSuccess: (definition: MlLabelDefinition) => void;
}

// Color picker preset colors
const presetColors = [
  '#ef4444', '#f97316', '#f59e0b', '#eab308', '#84cc16',
  '#22c55e', '#10b981', '#14b8a6', '#06b6d4', '#0ea5e9',
  '#3b82f6', '#6366f1', '#8b5cf6', '#a855f7', '#d946ef',
  '#ec4899', '#f43f5e',
];

function ColorPicker({ 
  value, 
  onChange 
}: { 
  value?: string | null; 
  onChange: (color: string | undefined) => void 
}) {
  const [showPicker, setShowPicker] = useState(false);
  
  return (
    <div className="relative">
      <button 
        onClick={() => setShowPicker(!showPicker)}
        className="h-8 w-8 rounded-md border border-border bg-bg-secondary flex items-center justify-center"
        style={{ backgroundColor: value || 'transparent' }}
      >
        {value ? null : <div className="h-4 w-4 rounded-full border border-border bg-bg-tertiary" />}
      </button>
      
      {showPicker && (
        <>
          <div 
            className="fixed inset-0 z-10"
            onClick={() => setShowPicker(false)}
          />
          <div className="absolute top-10 left-0 z-20 rounded-lg border border-border bg-bg-secondary p-2 shadow-lg">
            <div className="grid grid-cols-4 gap-1">
              {presetColors.map((color) => (
                <button
                  key={color}
                  onClick={() => {
                    onChange(color);
                    setShowPicker(false);
                  }}
                  className="h-6 w-6 rounded-md"
                  style={{ backgroundColor: color }}
                />
              ))}
              <button
                onClick={() => {
                  onChange(undefined);
                  setShowPicker(false);
                }}
                className="h-6 w-6 rounded-md border border-border bg-bg-tertiary flex items-center justify-center"
              >
                <X size={12} />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// Option input row for select/multiselect
interface OptionInputProps {
  value: string;
  displayName: string;
  color?: string | null;
  sortOrder: number;
  onRemove: () => void;
  onChange: (data: { value?: string; displayName?: string; color?: string | null; sortOrder?: number }) => void;
}

function OptionInput({ value, displayName, color, sortOrder, onRemove, onChange }: OptionInputProps) {
  return (
    <div className="flex items-center gap-2 p-2 rounded-lg border border-border bg-bg-secondary">
      <input
        type="text"
        value={value}
        onChange={(e) => onChange({ value: e.target.value })}
        placeholder="value"
        className="flex-1 text-[13px] bg-transparent border-none focus:ring-0 text-text-primary placeholder:text-text-tertiary"
      />
      <span className="text-text-tertiary">/</span>
      <input
        type="text"
        value={displayName}
        onChange={(e) => onChange({ displayName: e.target.value })}
        placeholder="Display Name"
        className="flex-1 text-[13px] bg-transparent border-none focus:ring-0 text-text-primary placeholder:text-text-tertiary"
      />
      <ColorPicker 
        value={color}
        onChange={(c) => onChange({ color: c || null })}
      />
      <input
        type="number"
        value={sortOrder}
        onChange={(e) => onChange({ sortOrder: parseInt(e.target.value) || 0 })}
        placeholder="Order"
        className="w-16 text-[13px] bg-transparent border-none focus:ring-0 text-text-primary placeholder:text-text-tertiary"
      />
      <Button 
        variant="ghost" 
        size="icon"
        onClick={onRemove}
        className="text-text-secondary hover:text-red-500"
      >
        <X size={14} />
      </Button>
    </div>
  );
}

// Validation helpers
function validateKey(key: string): string | null {
  if (!key) return 'Key is required';
  if (!/^[a-z][a-z0-9_]*$/.test(key)) {
    return 'Key must start with a letter and contain only lowercase letters, numbers, and underscores';
  }
  return null;
}

function validateName(name: string): string | null {
  if (!name) return 'Name is required';
  return null;
}

export function LabelDefinitionForm({ 
  definition, 
  onClose, 
  onSuccess 
}: LabelDefinitionFormProps) {
  const isEdit = !!definition;
  const [newOptions, setNewOptions] = useState<{ value: string; displayName: string; color?: string | null; sortOrder: number; }[]>([]);
  
  // Form state
  const [key, setKey] = useState(definition?.key || '');
  const [name, setName] = useState(definition?.name || '');
  const [description, setDescription] = useState(definition?.description || '');
  const [valueType, setValueType] = useState<LabelValueType>(definition?.value_type as LabelValueType || 'select');
  const [color, setColor] = useState<string | null>(definition?.color || null);
  const [isActive, setIsActive] = useState<boolean>(definition?.is_active ?? true);
  
  // Validation errors
  const [keyError, setKeyError] = useState<string | null>(null);
  const [nameError, setNameError] = useState<string | null>(null);
  
  const createMutation = useCreateLabelDefinition();
  const updateMutation = useUpdateLabelDefinition();
  const createOptionMutation = useCreateLabelOption();
  
  // Validate on change
  useEffect(() => {
    setKeyError(validateKey(key));
  }, [key]);
  
  useEffect(() => {
    setNameError(validateName(name));
  }, [name]);
  
  // Handle form submission
  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const keyErr = validateKey(key);
    const nameErr = validateName(name);
    
    if (keyErr) {
      setKeyError(keyErr);
      return;
    }
    if (nameErr) {
      setNameError(nameErr);
      return;
    }
    
    try {
      let result: MlLabelDefinition;
      
      if (isEdit && definition) {
        // Update existing definition
        result = await new Promise((resolve, reject) => {
          updateMutation.mutate(
            { 
              definitionId: definition.id, 
              key,
              name,
              description: description || null,
              value_type: valueType,
              color: color,
              is_active: isActive,
            },
            {
              onSuccess: (updated) => resolve(updated),
              onError: (error) => reject(error),
            }
          );
        });
      } else {
        // Create new definition
        result = await new Promise((resolve, reject) => {
          createMutation.mutate(
            { 
              key, 
              name, 
              value_type: valueType, 
              description: description || null, 
              color: color 
            },
            {
              onSuccess: (created) => resolve(created),
              onError: (error) => reject(error),
            }
          );
        });
      }
      
      // Create new options if any
      if (newOptions.length > 0) {
        for (const optionData of newOptions) {
          await new Promise((resolve, reject) => {
            createOptionMutation.mutate(
              { 
                definitionId: result.id, 
                value: optionData.value,
                display_name: optionData.displayName,
                color: optionData.color || null,
                sort_order: optionData.sortOrder,
              },
              {
                onSuccess: () => resolve(null),
                onError: (error) => reject(error),
              }
            );
          });
        }
      }
      
      onSuccess(result);
      onClose();
    } catch (error) {
      console.error('Failed to save label definition:', error);
    }
  };
  
  // Add a new empty option
  const addNewOption = () => {
    setNewOptions([...newOptions, { 
      value: '', 
      displayName: '', 
      color: null, 
      sortOrder: newOptions.length 
    }]);
  };
  
  // Remove an option
  const removeOption = (index: number) => {
    const updated = [...newOptions];
    updated.splice(index, 1);
    setNewOptions(updated);
  };
  
  // Update an option
  const updateOption = (index: number, data: { value?: string; displayName?: string; color?: string | null; sortOrder?: number }) => {
    setNewOptions(newOptions.map((option, i) => 
      i === index ? { ...option, ...data } : option
    ));
  };
  
  const isSubmitting = createMutation.isPending || updateMutation.isPending || createOptionMutation.isPending;
  const hasErrors = !!keyError || !!nameError;
  const isDisabled = hasErrors || isSubmitting;
  
  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div className="space-y-2">
        <label className="text-[12px] font-medium text-text-primary">
          Display Name *
        </label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g., Sentiment, Urgency, Topic"
          className={cn(
            'w-full rounded-lg border border-border bg-bg-secondary px-3 py-2 text-[14px] text-text-primary',
            'placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent-primary'
          )}
        />
        {nameError && (
          <p className="text-[12px] text-red-500">{nameError}</p>
        )}
      </div>
      
      <div className="space-y-2">
        <label className="text-[12px] font-medium text-text-primary">
          Key *
        </label>
        <input
          type="text"
          value={key}
          onChange={(e) => setKey(e.target.value)}
          placeholder="e.g., sentiment, urgency, topic"
          className={cn(
            'w-full rounded-lg border border-border bg-bg-secondary px-3 py-2 text-[14px] text-text-primary',
            'placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent-primary'
          )}
        />
        <p className="text-[11px] text-text-tertiary">
          Machine-readable identifier. Must be unique and use only lowercase letters, numbers, and underscores.
        </p>
        {keyError && (
          <p className="text-[12px] text-red-500">{keyError}</p>
        )}
      </div>
      
      <div className="space-y-2">
        <label className="text-[12px] font-medium text-text-primary">
          Description
        </label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Optional description of what this label dimension represents"
          rows={2}
          className={cn(
            'w-full rounded-lg border border-border bg-bg-secondary px-3 py-2 text-[14px] text-text-primary',
            'placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent-primary resize-none'
          )}
        />
      </div>
      
      <div className="space-y-2">
        <label className="text-[12px] font-medium text-text-primary">
          Value Type *
        </label>
        <select
          value={valueType}
          onChange={(e) => setValueType(e.target.value as LabelValueType)}
          className={cn(
            'w-full rounded-lg border border-border bg-bg-secondary px-3 py-2 text-[14px] text-text-primary',
            'placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent-primary'
          )}
        >
          <option value="select">Select (single choice from options)</option>
          <option value="multiselect">Multiselect (multiple choices from options)</option>
          <option value="text">Text (free-form text)</option>
          <option value="boolean">Boolean (true/false toggle)</option>
          <option value="number">Number (numeric value)</option>
        </select>
      </div>
      
      <div className="space-y-2">
        <label className="text-[12px] font-medium text-text-primary">
          Color
        </label>
        <ColorPicker 
          value={color}
          onChange={(c) => setColor(c || null)}
        />
      </div>
      
      <div className="space-y-2">
        <label className="flex items-center gap-2 text-[12px] font-medium text-text-primary">
          <input
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
            className="h-4 w-4 rounded border-border bg-bg-secondary text-accent-primary focus:ring-accent-primary"
          />
          <span>Active</span>
        </label>
      </div>
      
      {/* Options input for select/multiselect types */}
      {(valueType === 'select' || valueType === 'multiselect') && (
        <div className="space-y-3">
          <label className="text-[12px] font-medium text-text-primary">
            Options
          </label>
          <p className="text-[11px] text-text-tertiary">
            {valueType === 'select' 
              ? 'Define the allowed values for this single-select label.' 
              : 'Define the allowed values for this multi-select label.'
            }
          </p>
          
          <div className="space-y-2">
            {newOptions.map((option, index) => (
              <OptionInput
                key={index}
                {...option}
                onRemove={() => removeOption(index)}
                onChange={(data) => updateOption(index, data)}
              />
            ))}
            
            <Button 
              type="button" 
              variant="outline" 
              size="sm"
              onClick={addNewOption}
              className="w-full"
            >
              <Plus size={14} /> Add Option
            </Button>
          </div>
        </div>
      )}
      
      <div className="flex items-center justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onClose} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button type="submit" disabled={isDisabled}>
          {isEdit ? 'Save Changes' : 'Create Label'}
        </Button>
      </div>
    </form>
  );
}
