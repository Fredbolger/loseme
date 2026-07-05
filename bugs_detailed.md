# Detailed Bug Analysis (NPM Client Version)

## 1. Cannot scan without forcing re-index
**Description:** The scanning functionality appears to require a forced re-index operation, which is inefficient and may indicate issues with incremental indexing or state management.

**Relevant Files:**
- `client/npm/web-next/app/search/page.tsx` - Search functionality and API calls
- `client/npm/web-next/lib/search-store.ts` - Search state management
- `client/npm/web-next/hooks/useSearch.ts` - Search hooks and API integration
- `test_paperless_quick.py` - Paperless-specific indexing tests
- `email-pdf-processing-flow.md` - Indexing workflow documentation

**Potential Issues:**
- Missing or incorrect API endpoints for incremental scanning in the new client
- State management issues in Zustand store affecting scan triggers
- Paperless integration not properly handling incremental updates in the new architecture
- Search store not properly tracking indexing state

---

## 2. Chunks slider indicator misalignment
**Description:** The slider indicator for chunk size in the sources detailed view is positioned outside the slider track, creating a poor user experience.

**Relevant Files:**
- `client/npm/web-next/components/shared/DetailPanel.tsx` - Detail panel with chunk toggle slider
- `client/npm/web-next/components/storage/ChunkerCard.tsx` - Chunker visualization component
- CSS styling in Tailwind classes within the TSX components

**Potential Issues:**
- CSS positioning issues with the chunk toggle slider in DetailPanel.tsx (lines 143-158)
- Incorrect Tailwind classes for slider positioning
- Responsive design issues causing misalignment at certain screen sizes
- Missing proper slider component implementation

---

## 3. Preview generation not supported
**Description:** The detailed view cannot generate previews for any document type, suggesting a fundamental issue with the preview system.

**Relevant Files:**
- `client/npm/web-next/components/previews/` - Preview components:
  - `DocumentPreview.tsx` - Main preview component
  - `PlaintextPreview.tsx` - Plain text preview
  - `EmailPreview.tsx` - Email preview
  - `PdfFallbackPreview.tsx` - PDF preview fallback
- `client/npm/web-next/components/shared/DetailPanel.tsx` - Preview integration (line 184)
- `client/web/preview_proxy.py` - Backend preview proxy (still used by new client)

**Potential Issues:**
- Preview components not properly implemented or missing document type support
- DocumentPreview.tsx not routing to correct preview components
- Backend preview proxy not properly integrated with new client
- Missing preview generators for specific document types
- Fallback mechanism not working in DocumentPreview.tsx

---

## 4. Search functionality errors
**Description:** Search operations are failing with browser network errors, indicating API or backend issues.

**Relevant Files:**
- `client/npm/web-next/app/search/page.tsx` - Main search page with API calls
- `client/npm/web-next/hooks/useSearch.ts` - Search API hooks
- `client/npm/web-next/lib/api-client.ts` - API client configuration
- `client/npm/web-next/lib/search-store.ts` - Search state management
- `email-pdf-processing-flow.md` - Search workflow documentation

**Potential Issues:**
- Incorrect API endpoint URLs or parameters in the new client architecture
- Authentication/authorization issues with the new API client
- Backend service endpoints not compatible with new client expectations
- Error handling not properly implemented in useSearch.ts or search-store.ts
- Network request configuration issues in api-client.ts

---

## 5. LLM generation not working
**Description:** The LLM generation feature is completely non-functional.

**Relevant Files:**
- `client/npm/web-next/app/search/page.tsx` - LLM integration in search (lines 136-173)
- `client/npm/web-next/hooks/useSearch.ts` - LLM API calls and streaming
- `client/npm/web-next/hooks/useSSEStream.ts` - Server-Sent Events for LLM streaming
- `client/npm/web-next/lib/search-store.ts` - LLM state management
- `email-pdf-processing-flow.md` - LLM enrichment workflow

**Potential Issues:**
- LLM service not properly integrated with the new client architecture
- Missing or incorrect API endpoints for LLM operations in useSearch.ts
- SSE streaming not properly implemented in useSSEStream.ts
- LLM model selection and configuration issues
- State management problems in search-store.ts for LLM features

---

## 6. Paperless source configuration issues
**Description:** Two related issues with Paperless source configuration:
- Current settings not displayed correctly
- Available tags/document types not loading properly

**Relevant Files:**
- `client/npm/web-next/components/shared/SourceScopeEditor.tsx` - Main Paperless configuration component
- `client/npm/web-next/hooks/usePaperlessSourceScope.ts` - Paperless source scope hooks
- `client/npm/web-next/app/sources/page.tsx` - Sources page with Paperless integration
- `client/npm/web-next/components/shared/TagEditor.tsx` - Tag editing component
- `test_paperless_quick.py` - Paperless configuration tests
- `tests/test_paperless_tags.py` - Tag management tests

**Potential Issues:**
- Data loading issues in usePaperlessSourceScope.ts hooks:
  - `useAvailableTagsForSource`
  - `useAvailableCorrespondents`
  - `useAvailableDocumentTypes`
- State management problems in SourceScopeEditor.tsx (lines 68-126)
- API calls for fetching current settings failing
- Scope parsing and initialization issues (lines 106-126)
- Tag/document type endpoints not working with new client
- Data binding issues between hooks and UI components

---

## Next Investigation Steps

1. **API Client Verification:** Check API client configuration in `api-client.ts` and endpoint usage
2. **State Management Review:** Inspect Zustand stores (`search-store.ts`, `detail-panel-store.ts`) for proper state handling
3. **Preview System Audit:** Review new preview components and their integration with backend proxy
4. **Paperless Integration:** Verify Paperless-specific hooks and components in the new architecture
5. **LLM Integration:** Check LLM streaming implementation and state management
6. **Error Handling:** Improve error reporting throughout the new client components
7. **Component Testing:** Test individual components (SourceScopeEditor, DocumentPreview, etc.) for proper functionality