'use client';

import ReactMarkdown from 'react-markdown';
import { FileText, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/cn';
import type { ChatMessage as ChatMessageType, SourceRef } from '@/lib/types';

interface ChatMessageProps {
  message: ChatMessageType;
  streamingContent?: string;
  onSourcesClick?: (sources: SourceRef[]) => void;
}

/**
 * The legacy search-ui.js shipped a ~600-line inline <style> block with its
 * own gradient palette, font sizes, and bubble radii — visually a different
 * product from the Dashboard/Runs/Storage tabs. This component uses the
 * same shared tokens (Card surfaces, accent-primary, font-sans) as every
 * other view so Search finally looks like part of the same app.
 */
export function ChatMessage({ message, streamingContent, onSourcesClick }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const content = streamingContent !== undefined ? streamingContent : message.content;
  const isEmpty = !content && streamingContent !== undefined;

  return (
    <div className={cn('flex flex-col gap-1.5', isUser ? 'items-end' : 'items-start')}>
      <div
        className={cn(
          'max-w-[80%] rounded-2xl px-4 py-3 text-[14px] leading-relaxed',
          isUser
            ? 'rounded-br-md bg-accent-primary text-white'
            : 'rounded-bl-md border border-border bg-bg-secondary text-text-primary',
        )}
      >
        {isEmpty ? (
          <TypingIndicator />
        ) : isUser ? (
          <span className="whitespace-pre-wrap">{content}</span>
        ) : (
          <div className="prose prose-sm max-w-none prose-p:my-2 prose-p:text-text-primary prose-headings:text-text-primary prose-strong:text-text-primary prose-code:rounded prose-code:bg-bg-tertiary prose-code:px-1 prose-code:py-0.5 prose-code:text-accent-secondary prose-a:text-accent-primary">
            <ReactMarkdown>{content}</ReactMarkdown>
          </div>
        )}
      </div>

      {!isUser && message.sources && message.sources.length > 0 && (
        <button
          onClick={() => onSourcesClick?.(message.sources!)}
          className="inline-flex items-center gap-1.5 rounded-full border border-border bg-bg-tertiary px-3 py-1.5 text-[12px] font-medium text-text-secondary transition-colors hover:border-accent-primary hover:text-text-primary"
        >
          <FileText size={13} />
          {message.sources.length} source{message.sources.length !== 1 ? 's' : ''}
          <span className="rounded-full bg-accent-primary px-1.5 py-0.5 font-mono text-[10px] text-white">
            {Math.round((message.sources[0]?.score ?? 0) * 100)}%
          </span>
          <ChevronRight size={12} className="opacity-60" />
        </button>
      )}
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex gap-1 py-1">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 animate-bounce rounded-full bg-text-tertiary"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </div>
  );
}
