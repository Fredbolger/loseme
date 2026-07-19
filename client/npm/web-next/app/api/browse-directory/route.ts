// client/npm/web-next/app/api/browse-directory/route.ts
import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import { hostPathToContainer } from '@/lib/docker-path-translation';

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    let hostPath = searchParams.get('path') || '';

    const hostRoot = process.env.LOSEME_HOST_ROOT;
    if (!hostRoot) {
      return NextResponse.json(
        { error: 'LOSEME_HOST_ROOT environment variable is not set' },
        { status: 500 }
      );
    }

    // Default to root if no path provided
    if (!hostPath) {
      hostPath = hostRoot;
    }

    // Resolve to absolute host path
    const absoluteHostPath = path.resolve(hostPath);

    // Translate to container path; throws if outside LOSEME_HOST_ROOT
    const containerPath = hostPathToContainer(absoluteHostPath);

    const entries = fs.readdirSync(containerPath, { withFileTypes: true });

    const directories = entries
      .filter((entry) => entry.isDirectory() && !entry.name.startsWith('.'))
      .map((entry) => ({
        name: entry.name,
        host_path: path.join(absoluteHostPath, entry.name),
      }))
      .sort((a, b) => a.name.localeCompare(b.name));

    const parentPath =
      absoluteHostPath !== hostRoot ? path.dirname(absoluteHostPath) : null;

    return NextResponse.json({
      current_path: absoluteHostPath,
      parent_path: parentPath,
      root_path: hostRoot,
      directories,
    });
  } catch (error: any) {
    let status = 400;
    let message = 'Failed to browse directory';

    if (error.code === 'ENOENT') {
      status = 404;
      message = 'Directory not found';
    } else if (error.message?.includes('under the configured host root')) {
      // hostPathToContainer throws this when path is outside root
      status = 403;
      message = 'Path is outside allowed root';
    } else {
      message = error.message || message;
    }

    return NextResponse.json({ error: message }, { status });
  }
}
