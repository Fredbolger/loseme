/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // This app must run on the SAME device/container that owns the source files,
  // exactly like the old FastAPI client (client/web/main.py + preview_proxy.py).
  // Do not deploy this as a shared/centralized server unless LOSEME_HOST_ROOT
  // points at storage genuinely reachable from this process.
};

module.exports = nextConfig;
