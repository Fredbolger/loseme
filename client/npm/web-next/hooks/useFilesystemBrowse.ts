// client/npm/web-next/hooks/useFilesystemBrowse.ts
import { useQuery } from '@tanstack/react-query';

export interface BrowseDirectoryResponse {
  current_path: string;
  parent_path: string | null;
  root_path: string;
  directories: Array<{ name: string; host_path: string }>;
}

/** Fetch a directory listing from the /api/browse-directory endpoint. */
export function useBrowseDirectory(hostPath: string | null) {
  return useQuery<BrowseDirectoryResponse>({
    queryKey: ['browse-directory', hostPath],
    queryFn: async () => {
      const url = hostPath
        ? `/api/browse-directory?path=${encodeURIComponent(hostPath)}`
        : '/api/browse-directory';
      const res = await fetch(url);
      if (!res.ok) {
        const error = await res.json().catch(() => ({ error: 'Unknown error' }));
        throw new Error(error.error || `HTTP ${res.status}`);
      }
      return res.json();
    },
    enabled: hostPath !== undefined, // Allow null to fetch root
    staleTime: 60_000, // Cache directory listings for 1 minute
  });
}
