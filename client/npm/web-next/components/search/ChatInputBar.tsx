'use client';

import { useRef, KeyboardEvent } from 'react';
import { Send } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Select, TextInput } from '@/components/ui/Select';
import { useSearchStore } from '@/lib/search-store';

interface ChatInputBarProps {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  disabled?: boolean;
  models: string[];
}

export function ChatInputBar({ value, onChange, onSend, disabled, models }: ChatInputBarProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { searchMode, setSearchMode, topK, setTopK, selectedModel, setModel } = useSearchStore();

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !disabled) onSend();
    }
  }

  return (
    <div className="border-t border-border bg-bg-primary px-6 py-4">
      <div className="mx-auto flex max-w-3xl flex-col gap-2.5">
        <div className="relative">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about your documents…"
            rows={1}
            className="max-h-[200px] min-h-[52px] w-full resize-none rounded-xl border-2 border-border bg-bg-secondary px-4 py-3 pr-14 text-[14px] text-text-primary outline-none transition-colors placeholder:text-text-tertiary focus:border-accent-primary"
          />
          <Button
            variant="primary"
            size="icon"
            className="absolute bottom-2.5 right-2.5 rounded-full"
            disabled={!value.trim() || disabled}
            onClick={onSend}
          >
            <Send size={15} />
          </Button>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <Select value={searchMode} onChange={(e) => setSearchMode(e.target.value as 'hybrid' | 'search')}>
            <option value="hybrid">🤖 Hybrid (LLM + Search)</option>
            <option value="search">📄 Search only</option>
          </Select>

          <label className="flex items-center gap-1.5 text-[11px] text-text-tertiary">
            Top K
            <TextInput
              type="number"
              min={1}
              max={50}
              value={topK}
              onChange={(e) => setTopK(parseInt(e.target.value) || 10)}
              className="w-20"
            />
          </label>

          {searchMode === 'hybrid' && models.length > 0 && (
            <Select value={selectedModel ?? ''} onChange={(e) => setModel(e.target.value)}>
              {models.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </Select>
          )}

          <span className="ml-auto text-[11px] text-text-tertiary">
            Enter to send · Shift+Enter for new line
          </span>
        </div>
      </div>
    </div>
  );
}
