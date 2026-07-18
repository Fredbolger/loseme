'use client';
import { MessageSquare } from 'lucide-react';

const SUGGESTIONS = [
  'What documents do I have?',
  'Summarize my recent files',
  'Find information about...',
];

export function WelcomeScreen({ onPick }: { onPick: (text: string) => void }) {
  return (
    <div className="mx-auto flex max-w-lg flex-1 flex-col items-center justify-center gap-4 px-6 text-center">
      <MessageSquare size={40} className="text-accent-primary" />
      <h2 className="font-display text-2xl font-bold text-text-primary">How can I help you today?</h2>
      <p className="text-[14px] leading-relaxed text-text-secondary">
        Ask me anything about your documents — I&apos;ll search and provide answers with sources.
      </p>
      <div className="flex flex-wrap justify-center gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onPick(s)}
            className="rounded-full border border-border bg-bg-tertiary px-4 py-2 text-[13px] font-medium text-text-secondary transition-colors hover:border-accent-primary hover:bg-accent-primary hover:text-white"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
