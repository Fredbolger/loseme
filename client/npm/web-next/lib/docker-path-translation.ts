import path from 'node:path';
import fs from 'node:fs';

/**
 * Ported from core/loseme_core/docker_path_translation.py and
 * client/sources/base/docker_path_translation.py.
 *
 * IMPORTANT: this must only be called from server-side code (Route
 * Handlers / Server Components), never from the browser, since it reads
 * env vars and the local filesystem of whatever device this Next.js
 * process runs on. Mirrors the original constraint that the web client
 * must run on the same machine as the files it previews.
 */

export function isRunningInDocker(): boolean {
  return fs.existsSync('/.dockerenv');
}

function requireRoots(): { hostRoot: string; containerRoot: string } {
  const hostRoot = process.env.LOSEME_HOST_ROOT;
  const containerRoot = process.env.LOSEME_CONTAINER_ROOT;
  if (!hostRoot || !containerRoot) {
    throw new Error(
      'LOSEME_HOST_ROOT and LOSEME_CONTAINER_ROOT environment variables must be set',
    );
  }
  return { hostRoot: path.resolve(hostRoot), containerRoot: path.resolve(containerRoot) };
}

export function hostPathToContainer(hostPath: string): string {
  const { hostRoot, containerRoot } = requireRoots();
  const resolved = path.resolve(hostPath);

  if (!path.isAbsolute(resolved)) {
    throw new Error(`Host path must be absolute: ${resolved}`);
  }
  const relative = path.relative(hostRoot, resolved);
  if (relative.startsWith('..') || path.isAbsolute(relative)) {
    throw new Error(`Host path ${resolved} is not under the configured host root ${hostRoot}`);
  }
  return path.join(containerRoot, relative);
}

export function containerPathToHost(containerPath: string): string {
  const { hostRoot, containerRoot } = requireRoots();
  const resolved = path.resolve(containerPath);

  if (!path.isAbsolute(resolved)) {
    throw new Error(`Container path must be absolute: ${resolved}`);
  }
  const relative = path.relative(containerRoot, resolved);
  if (relative.startsWith('..') || path.isAbsolute(relative)) {
    throw new Error(
      `Container path ${resolved} is not under the configured container root ${containerRoot}`,
    );
  }
  return path.join(hostRoot, relative);
}
