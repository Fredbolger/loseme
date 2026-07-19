'use client';

import { useState, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import * as Dialog from '@radix-ui/react-dialog';
import { Loader2, FolderOpen, ArrowUp, ChevronRight, X } from 'lucide-react';
import { useBrowseDirectory } from '@/hooks/useFilesystemBrowse';
import { useAddFilesystemSource, useScanSource } from '@/hooks/useDashboard';

interface AddFilesystemSourceDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function AddFilesystemSourceDialog({
  open,
  onOpenChange,
  onSuccess,
}: AddFilesystemSourceDialogProps) {
  const qc = useQueryClient();

  const [currentPath, setCurrentPath] = useState<string | null>(null);
  const { data, isLoading, error, refetch } = useBrowseDirectory(currentPath);

  const [selectedDirectory, setSelectedDirectory] = useState<string | null>(null);
  const [recursive, setRecursive] = useState(true);
  const [includePatterns, setIncludePatterns] = useState<string[]>([]);
  const [excludePatterns, setExcludePatterns] = useState<string[]>([]);
  const [includeInput, setIncludeInput] = useState('');
  const [excludeInput, setExcludeInput] = useState('');

  const addSource = useAddFilesystemSource();
  const scanSource = useScanSource();

  useEffect(() => {
    if (open) {
      setCurrentPath(null);
      setSelectedDirectory(null);
      setRecursive(true);
      setIncludePatterns([]);
      setExcludePatterns([]);
      setIncludeInput('');
      setExcludeInput('');
      refetch();
    }
  }, [open, refetch]);

  const handleSelectDirectory = (hostPath: string) => setSelectedDirectory(hostPath);
  const handleNavigate = (hostPath: string) => {
    setCurrentPath(hostPath);
    setSelectedDirectory(null);
  };
  const handleGoUp = () => {
    if (data?.parent_path) {
      setCurrentPath(data.parent_path);
      setSelectedDirectory(null);
    }
  };

  const addPattern = (
    pattern: string,
    setPatterns: React.Dispatch<React.SetStateAction<string[]>>,
    setInput: React.Dispatch<React.SetStateAction<string>>
  ) => {
    const trimmed = pattern.trim();
    if (trimmed && !setPatterns.toString().includes(trimmed)) {
      setPatterns((prev) => [...prev, trimmed]);
      setInput('');
    }
  };

  const removePattern = (pattern: string, setPatterns: React.Dispatch<React.SetStateAction<string[]>>) => {
    setPatterns((prev) => prev.filter((p) => p !== pattern));
  };

  const handleSubmit = async () => {
    if (!selectedDirectory) {
      toast.error('Please select a directory first');
      return;
    }
    try {
      const result = await addSource.mutateAsync({
        directory: selectedDirectory,
        recursive,
        includePatterns,
        excludePatterns,
      });
      if (result.source_id) {
        await scanSource.mutateAsync({ sourceId: result.source_id, forceReprocess: false });
      }
      onOpenChange(false);
      if (onSuccess) onSuccess();
      qc.invalidateQueries({ queryKey: ['sources', 'all'] });
      qc.invalidateQueries({ queryKey: ['documents'] });
    } catch (err) {
      // handled by mutations
    }
  };

  const isSubmitting = addSource.isPending || scanSource.isPending;
  const isAddDisabled = !selectedDirectory || isSubmitting;

  const renderBreadcrumb = () => {
    const path = data?.current_path || '';
    const segments = path.split('/').filter(Boolean);
    return (
      <div className="flex items-center space-x-1 text-sm text-gray-600 truncate">
        <FolderOpen className="h-4 w-4 mr-1" />
        {segments.map((seg, idx) => (
          <span key={idx} className="truncate">
            {idx > 0 && <ChevronRight className="inline h-3 w-3 mx-1" />}
            {seg}
          </span>
        ))}
      </div>
    );
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/60 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
        <Dialog.Content className="fixed left-[50%] top-[50%] max-h-[85vh] w-[90vw] max-w-2xl translate-x-[-50%] translate-y-[-50%] rounded-lg bg-white p-6 shadow-xl border border-gray-200 focus:outline-none data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%] data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%] flex flex-col">
          <Dialog.Title className="text-lg font-semibold text-gray-900">Add Filesystem Source</Dialog.Title>

          {/* Directory browser */}
          <div className="flex-1 min-h-0 border border-gray-200 rounded-md p-2 mt-4 bg-gray-50">
            <div className="flex items-center justify-between mb-2">
              {renderBreadcrumb()}
              {data?.parent_path && (
                <button
                  onClick={handleGoUp}
                  className="inline-flex items-center px-2 py-1 text-sm rounded hover:bg-gray-200 transition-colors"
                >
                  <ArrowUp className="h-4 w-4 mr-1" />
                  Up
                </button>
              )}
            </div>

            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-gray-500" />
              </div>
            ) : error ? (
              <div className="text-center py-8 text-red-600">
                <p>Failed to load directory</p>
                <p className="text-sm">{error.message}</p>
                <button
                  onClick={() => refetch()}
                  className="mt-2 inline-flex items-center px-3 py-1 text-sm rounded border border-gray-300 hover:bg-gray-100 transition-colors"
                >
                  Retry
                </button>
              </div>
            ) : data && data.directories.length === 0 ? (
              <div className="text-center py-8 text-gray-500">No subdirectories found</div>
            ) : (
              <ul className="space-y-1 max-h-60 overflow-y-auto">
                {data?.directories.map((dir) => (
                  <li
                    key={dir.host_path}
                    className={`flex items-center justify-between p-2 rounded cursor-pointer hover:bg-gray-100 transition-colors ${
                      selectedDirectory === dir.host_path ? 'bg-blue-50 border border-blue-200' : ''
                    }`}
                    onClick={() => handleSelectDirectory(dir.host_path)}
                    onDoubleClick={() => handleNavigate(dir.host_path)}
                  >
                    <span className="flex items-center">
                      <FolderOpen className="h-4 w-4 mr-2 text-gray-500" />
                      {dir.name}
                    </span>
                    <div className="flex items-center gap-1">
                      <button
                        className="px-2 py-1 text-sm rounded hover:bg-gray-200 transition-colors"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleNavigate(dir.host_path);
                        }}
                      >
                        Open
                      </button>
                      <button
                        className={`px-2 py-1 text-sm rounded transition-colors ${
                          selectedDirectory === dir.host_path
                            ? 'bg-blue-600 text-white hover:bg-blue-700'
                            : 'border border-gray-300 hover:bg-gray-100'
                        }`}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleSelectDirectory(dir.host_path);
                        }}
                      >
                        Select
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {selectedDirectory && (
            <div className="text-sm mt-2 text-gray-700">
              Selected: <span className="font-mono text-xs bg-gray-100 px-2 py-0.5 rounded">{selectedDirectory}</span>
            </div>
          )}

          {/* Options */}
          <div className="space-y-3 mt-3">
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="recursive"
                checked={recursive}
                onChange={(e) => setRecursive(e.target.checked)}
                className="rounded border-gray-300"
              />
              <label htmlFor="recursive" className="text-sm font-medium text-gray-700">
                Recursive (index subdirectories)
              </label>
            </div>

            {/* Include patterns */}
            <div>
              <label className="text-sm font-medium text-gray-700">Include patterns (glob)</label>
              <div className="flex gap-2 mt-1">
                <input
                  type="text"
                  placeholder="e.g. *.md, src/**/*.ts"
                  value={includeInput}
                  onChange={(e) => setIncludeInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      addPattern(includeInput, setIncludePatterns, setIncludeInput);
                    }
                  }}
                  className="flex-1 rounded border border-gray-300 px-3 py-1 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
                <button
                  className="px-3 py-1 text-sm rounded border border-gray-300 hover:bg-gray-100 transition-colors"
                  onClick={() => addPattern(includeInput, setIncludePatterns, setIncludeInput)}
                >
                  Add
                </button>
              </div>
              <div className="flex flex-wrap gap-1 mt-1">
                {includePatterns.map((pat) => (
                  <span
                    key={pat}
                    className="inline-flex items-center bg-blue-100 text-blue-800 px-2 py-0.5 rounded text-xs"
                  >
                    {pat}
                    <button
                      type="button"
                      className="ml-1 hover:text-red-600"
                      onClick={() => removePattern(pat, setIncludePatterns)}
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                ))}
              </div>
            </div>

            {/* Exclude patterns */}
            <div>
              <label className="text-sm font-medium text-gray-700">Exclude patterns (glob)</label>
              <div className="flex gap-2 mt-1">
                <input
                  type="text"
                  placeholder="e.g. node_modules, **/*.log"
                  value={excludeInput}
                  onChange={(e) => setExcludeInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      addPattern(excludeInput, setExcludePatterns, setExcludeInput);
                    }
                  }}
                  className="flex-1 rounded border border-gray-300 px-3 py-1 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
                <button
                  className="px-3 py-1 text-sm rounded border border-gray-300 hover:bg-gray-100 transition-colors"
                  onClick={() => addPattern(excludeInput, setExcludePatterns, setExcludeInput)}
                >
                  Add
                </button>
              </div>
              <div className="flex flex-wrap gap-1 mt-1">
                {excludePatterns.map((pat) => (
                  <span
                    key={pat}
                    className="inline-flex items-center bg-red-100 text-red-800 px-2 py-0.5 rounded text-xs"
                  >
                    {pat}
                    <button
                      type="button"
                      className="ml-1 hover:text-red-600"
                      onClick={() => removePattern(pat, setExcludePatterns)}
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                ))}
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-2 mt-4 border-t border-gray-200 pt-4">
            <Dialog.Close asChild>
              <button className="px-4 py-2 text-sm rounded border border-gray-300 hover:bg-gray-100 transition-colors">
                Cancel
              </button>
            </Dialog.Close>
            <button
              onClick={handleSubmit}
              disabled={isAddDisabled}
              className="px-4 py-2 text-sm rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 inline animate-spin" />
                  Adding & Scanning…
                </>
              ) : (
                'Add Source'
              )}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
