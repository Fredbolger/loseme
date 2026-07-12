// Ported from core/loseme_core/document_models.py, models.py,
// server/preview/models.py, server/storage/metadata_db/*.py

export type SourceType = 'filesystem' | 'thunderbird' | 'paperless';

export interface DocumentPart {
  document_part_id: string;
  source_type: SourceType;
  checksum: string;
  device_id: string;
  source_path: string;
  source_instance_id: string;
  unit_locator: string;
  content_type: string;
  extractor_name: string;
  extractor_version: string;
  metadata_json?: Record<string, unknown>;
  chunker_name?: string | null;
  chunker_version?: string | null;
  chunk_ids?: string | null; // JSON-encoded string[] as stored in sqlite
  created_at: string;
  updated_at: string;
  last_indexed_at?: string | null;
  text?: string;
  scope_json?: string;
}

export interface Chunk {
  id: string;
  source_type: string;
  source_path: string;
  text?: string;
  document_part_id: string;
  device_id: string;
  unit_locator: string;
  index: number;
  metadata: Record<string, unknown>;
}

export type RunStatus =
  | 'pending'
  | 'running'
  | 'starting'
  | 'completed'
  | 'interrupted'
  | 'failed'
  | 'stop_requested';

export interface IndexingRunSummary {
  run_id: string;
  source_type: SourceType;
  status: RunStatus;
  started_at: string;
  updated_at: string;
  discovered_document_count: number;
  indexed_document_count: number;
}

export interface FilesystemScope {
  type: 'filesystem';
  directories: string[];
  recursive: boolean;
  include_patterns: string[];
  exclude_patterns: string[];
}

export interface ThunderbirdScope {
  type: 'thunderbird';
  mbox_path: string;
  ignore_patterns?: { field: string; value: string }[] | null;
}

export interface PaperlessScope {
  type: 'paperless';
  connection_id: string;
  tag_ids?: number[] | null;
  correspondent_ids?: number[] | null;
  document_type_ids?: number[] | null;
}

export type IndexingScopeDTO = FilesystemScope | ThunderbirdScope | PaperlessScope | (Record<string, unknown> & { type: string });

export interface MonitoredSource {
  id: string;
  source_type: SourceType;
  locator: string;
  scope: IndexingScopeDTO;
  last_seen_fingerprint?: string | null;
  last_checked_at?: string | null;
  last_ingested_at?: string | null;
  enabled: boolean;
  created_at: string;
  device_id?: string | null;
}

export interface PreviewResult {
  source_type: SourceType;
  preview_type: 'email' | 'plaintext' | 'pdf' | 'paperless_document' | 'paperless_pdf' | 'paperless_image' | string;
  subject?: string;
  from_?: string;
  to?: string;
  date?: string;
  body_html?: string;
  body_text?: string;
  text?: string;
  language?: string;
  meta?: Record<string, unknown>;
  source_path?: string;
  // Paperless-specific fields
  paperless_document_id?: string;
  connection_id?: string;
}

export interface DocumentStats {
  total_document_parts: number;
  total_sources: number;
  total_devices: number;
}

export interface StatsPerSource {
  source_id: string;
  source_type: SourceType;
  scope_json: string;
  document_part_count: number;
}

export interface ChunkerStat {
  chunker_name: string | null;
  chunker_version: string | null;
  document_part_count: number;
}

export interface HistogramBucket {
  label: string;
  count: number;
}

export interface DistributionStats {
  count?: number;
  min?: number;
  max?: number;
  mean?: number;
  p50?: number;
  p95?: number;
}

export interface ChunkDistributionResponse {
  char_len_histogram: HistogramBucket[];
  chunks_per_doc_histogram: HistogramBucket[];
  stats: DistributionStats;
  total_chunks: number;
}

// ── Search domain ──────────────────────────────────────────────

export interface SearchResultRaw {
  chunk_id: string;
  document_part_id: string;
  device_id: string;
  score: number;
  metadata: Record<string, unknown>;
  source_path: string;
  source_type: SourceType;
  unit_locator: string;
  chunk_text: string;
}

export interface MergedSearchResult extends SearchResultRaw {
  chunks: SearchResultRaw[];
  maxScore: number;
  minScore: number;
  chunkCount: number;
  allChunkTexts: string[];
}

export interface SourceRef {
  document_part_id: string;
  source_path: string;
  source_type: SourceType;
  score: number;
  chunk_count: number;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: SourceRef[];
  created_at: string;
}

export interface SessionSummary {
  session_id: string;
  query: string;
  result_count: number;
  message_count: number;
  updated_at: string;
  title?: string | null;
}

// Paperless Tag Management Types
export interface PaperlessTag {
  id: number;
  name: string;
  slug?: string;
  color?: string | null;
  text_color?: string | null;
}

export interface PaperlessCorrespondent {
  id: number;
  name: string;
}

export interface PaperlessDocumentType {
  id: number;
  name: string;
}

export interface DocumentTagData {
  tag_ids: number[];
  tags: PaperlessTag[];
}

// Paperless Source Scope Types
export interface PaperlessSourceScope {
  tag_ids: number[] | null;
  correspondent_ids: number[] | null;
  document_type_ids: number[] | null;
}
