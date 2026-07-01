/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // This app must run on the SAME device/container that owns the source files,
  // exactly like the old FastAPI client (client/web/main.py + preview_proxy.py).
  // Do not deploy this as a shared/centralized server unless LOSEME_HOST_ROOT
  // points at storage genuinely reachable from this process.
  env: {
    LOSEME_API_URL: process.env.LOSEME_API_URL || 'http://localhost:8000',
    LOSEME_API_KEY: process.env.LOSEME_API_KEY || '',
    LOSEME_CLIENT_URL: process.env.LOSEME_CLIENT_URL || 'http://localhost:3000',
    LOSEME_HOST_ROOT: process.env.LOSEME_HOST_ROOT || '',
    LOSEME_CONTAINER_ROOT: process.env.LOSEME_CONTAINER_ROOT || '',
    LOSEME_DEVICE_ID: process.env.LOSEME_DEVICE_ID || '',
  },
};

module.exports = nextConfig;
