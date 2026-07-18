'use client';

import { useState } from 'react';
import { Plus } from 'lucide-react';
import { useLabelDefinitions, useLabelStatistics } from '@/hooks/useMlLabels';
import { Button } from '@/components/ui/Button';
import { LoadingState } from '@/components/ui/States';
import { LabelDefinitionCard } from '@/components/labels/LabelDefinitionCard';
import { LabelDefinitionForm } from '@/components/labels/LabelDefinitionForm';
import type { MlLabelDefinition, MlLabelOption, MlLabelStatistic } from '@/lib/types';

// Dialog component (simplified version)
function Dialog({ 
  open, 
  onOpenChange, 
  children 
}: { 
  open: boolean; 
  onOpenChange: (open: boolean) => void; 
  children: React.ReactNode; 
}) {
  if (!open) return null;
  
  return (
    <>
      <div 
        className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
        onClick={() => onOpenChange(false)}
      />
      <div className="fixed inset-0 z-[51] flex items-center justify-center p-4" onClick={(e) => e.stopPropagation()}>
        <div 
          className="relative w-full max-w-lg rounded-xl border border-border bg-bg-secondary shadow-xl"
          onClick={(e) => e.stopPropagation()}
        >
          {children}
        </div>
      </div>
    </>
  );
}

function DialogHeader({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between border-b border-border px-6 py-4">
      {children}
    </div>
  );
}

function DialogContent({ children }: { children: React.ReactNode }) {
  return (
    <div className="p-6">
      {children}
    </div>
  );
}

function DialogTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-[16px] font-semibold text-text-primary">
      {children}
    </h2>
  );
}

// Option form dialog
function OptionFormDialog({ 
  open, 
  onOpenChange, 
  definition, 
  option,
  onSuccess 
}: { 
  open: boolean; 
  onOpenChange: (open: boolean) => void; 
  definition: MlLabelDefinition | null;
  option?: MlLabelOption | null;
  onSuccess: () => void;
}) {
  const [value, setValue] = useState(option?.value || '');
  const [displayName, setDisplayName] = useState(option?.display_name || '');
  const [color, setColor] = useState(option?.color || '');
  const [sortOrder, setSortOrder] = useState<number>(option?.sort_order ?? 0);
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // For now, just close the dialog
    // In a full implementation, this would call useCreateLabelOption or useUpdateLabelOption
    onSuccess();
    onOpenChange(false);
  };
  
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogHeader>
        <DialogTitle>
          {option ? 'Edit Option' : 'Add Option'}
        </DialogTitle>
      </DialogHeader>
      <DialogContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="text-[12px] font-medium text-text-primary">
              Value *
            </label>
            <input
              type="text"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder="e.g., positive"
              className="w-full rounded-lg border border-border bg-bg-secondary px-3 py-2 text-[14px] text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent-primary"
            />
          </div>
          
          <div className="space-y-2">
            <label className="text-[12px] font-medium text-text-primary">
              Display Name *
            </label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="e.g., Positive"
              className="w-full rounded-lg border border-border bg-bg-secondary px-3 py-2 text-[14px] text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent-primary"
            />
          </div>
          
          <div className="space-y-2">
            <label className="text-[12px] font-medium text-text-primary">
              Sort Order
            </label>
            <input
              type="number"
              value={sortOrder}
              onChange={(e) => setSortOrder(parseInt(e.target.value) || 0)}
              className="w-full rounded-lg border border-border bg-bg-secondary px-3 py-2 text-[14px] text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent-primary"
            />
          </div>
          
          <div className="flex items-center justify-end gap-2">
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit">
              {option ? 'Save Changes' : 'Add Option'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default function LabelsPage() {
  const [showForm, setShowForm] = useState(false);
  const [editingDefinition, setEditingDefinition] = useState<MlLabelDefinition | null>(null);
  const [showOptionForm, setShowOptionForm] = useState(false);
  const [editingOptionDefinition, setEditingOptionDefinition] = useState<MlLabelDefinition | null>(null);
  const [editingOption, setEditingOption] = useState<MlLabelOption | null>(null);
  
  const { data: definitions, isLoading, error } = useLabelDefinitions(true);
  const { data: statistics, isLoading: statsLoading } = useLabelStatistics(null);
  
  const handleCreate = () => {
    setEditingDefinition(null);
    setShowForm(true);
  };
  
  const handleEdit = (definition: MlLabelDefinition) => {
    setEditingDefinition(definition);
    setShowForm(true);
  };
  
  const handleAddOption = (definition: MlLabelDefinition) => {
    setEditingOptionDefinition(definition);
    setEditingOption(null);
    setShowOptionForm(true);
  };
  
  const handleEditOption = (option: MlLabelOption) => {
    // Find the parent definition
    const parentDefinition = definitions?.find(d => d.id === option.definition_id);
    if (parentDefinition) {
      setEditingOptionDefinition(parentDefinition);
      setEditingOption(option);
      setShowOptionForm(true);
    }
  };
  
  const handleFormSuccess = (definition: MlLabelDefinition) => {
    setShowForm(false);
    setEditingDefinition(null);
    // The mutation will automatically invalidate the cache
  };
  
  const handleOptionFormSuccess = () => {
    setShowOptionForm(false);
    setEditingOptionDefinition(null);
    setEditingOption(null);
  };
  
  if (isLoading) {
    return <LoadingState label="Loading label definitions..." />;
  }
  
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <p className="text-[14px] text-red-500">
          Failed to load label definitions
        </p>
        <Button onClick={() => window.location.reload()} className="mt-4">
          Retry
        </Button>
      </div>
    );
  }
  
  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-6 py-4">
        <h1 className="text-[20px] font-bold text-text-primary">
          ML Labels
        </h1>
        <Button onClick={handleCreate}>
          <Plus size={16} /> New Label
        </Button>
      </div>
      
      {/* Statistics Summary */}
      {!statsLoading && statistics?.length ? (
        <div className="border-b border-border px-6 py-3">
          <div className="flex flex-wrap gap-6 text-[12px] text-text-secondary">
            {definitions?.map((definition) => {
              const defStats = statistics.filter(s => s.definition_id === definition.id);
              const total = defStats.reduce((sum, s) => sum + s.count, 0);
              return (
                <div key={definition.id} className="flex items-center gap-2">
                  <span className="font-medium text-text-primary">{definition.name}:</span>
                  {defStats.map((stat, idx) => (
                    <span key={stat.option_id || stat.option_value || idx} className="flex items-center gap-1">
                      {stat.option_display_name || stat.option_value || 'N/A'}: {stat.count}
                      {idx < defStats.length - 1 && <span>,</span>}
                    </span>
                  ))}
                  <span className="text-text-tertiary">({total} total)</span>
                </div>
              );
            })}
          </div>
        </div>
      ) : null}
      
      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {definitions && definitions.length > 0 ? (
          <div className="grid gap-4 max-w-4xl">
            {definitions.map((definition) => {
              const defStats = statistics?.filter(s => s.definition_id === definition.id) || [];
              return (
                <LabelDefinitionCard
                  key={definition.id}
                  definition={definition}
                  onEdit={handleEdit}
                  onAddOption={handleAddOption}
                  onEditOption={handleEditOption}
                  statistics={defStats}
                />
              );
            })}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center gap-4 px-6 py-16 text-center">
            <div className="text-[14px] font-medium text-text-secondary">
              No label definitions yet
            </div>
            <div className="max-w-xs text-[12px] text-text-tertiary">
              Create your first label dimension to start organizing your documents
            </div>
            <Button onClick={handleCreate}>
              <Plus size={16} /> Create Label
            </Button>
          </div>
        )}
      </div>
      
      {/* Create/Edit Definition Form */}
      <Dialog open={showForm} onOpenChange={setShowForm}>
        <DialogHeader>
          <DialogTitle>
            {editingDefinition ? 'Edit Label Definition' : 'Create New Label Definition'}
          </DialogTitle>
        </DialogHeader>
        <DialogContent>
          <LabelDefinitionForm
            definition={editingDefinition || null}
            onClose={() => setShowForm(false)}
            onSuccess={handleFormSuccess}
          />
        </DialogContent>
      </Dialog>
      
      {/* Option Form */}
      <OptionFormDialog
        open={showOptionForm}
        onOpenChange={setShowOptionForm}
        definition={editingOptionDefinition}
        option={editingOption || null}
        onSuccess={handleOptionFormSuccess}
      />
    </div>
  );
}
