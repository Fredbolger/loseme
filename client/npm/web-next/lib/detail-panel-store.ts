import { create } from 'zustand';
import type { SourceType } from '@/lib/types';

export interface DetailDoc {
  document_part_id: string;
  source_type: SourceType;
  source_path: string;
}

interface DetailPanelState {
  isOpen: boolean;
  docs: DetailDoc[];
  activeIndex: number;
  chunksOpen: boolean;
  open: (docId: string, docs: DetailDoc[]) => void;
  close: () => void;
  navigate: (direction: 1 | -1) => void;
  toggleChunks: (force?: boolean) => void;
}

export const useDetailPanelStore = create<DetailPanelState>((set, get) => ({
  isOpen: false,
  docs: [],
  activeIndex: -1,
  chunksOpen: false,

  open: (docId, docs) => {
    let idx = docs.findIndex((d) => d.document_part_id === docId);
    let list = docs;
    if (idx === -1) {
      list = docs.length ? docs : [{ document_part_id: docId, source_type: 'filesystem', source_path: '' }];
      idx = list.findIndex((d) => d.document_part_id === docId);
      if (idx === -1) idx = 0;
    }
    set({ isOpen: true, docs: list, activeIndex: idx });
  },

  close: () => set({ isOpen: false, chunksOpen: false }),

  navigate: (direction) => {
    const { docs, activeIndex } = get();
    const next = activeIndex + direction;
    if (next < 0 || next >= docs.length) return;
    set({ activeIndex: next });
  },

  toggleChunks: (force) => set((s) => ({ chunksOpen: force ?? !s.chunksOpen })),
}));
