# Multi-stage build for Next.js

# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY client/npm/web-next/package.json client/npm/web-next/package-lock.json ./
RUN npm ci
COPY client/npm/web-next .
RUN npm run build

# Runtime stage
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV production
# Copy build artifacts from builder
COPY --from=builder /app/.next ./.next
#COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/node_modules ./node_modules
# Copy necessary source files for runtime (don't copy .next from source)
COPY client/npm/web-next/app ./app
COPY client/npm/web-next/components ./components
COPY client/npm/web-next/lib ./lib
COPY client/npm/web-next/hooks ./hooks
COPY client/npm/web-next/styles ./styles
COPY client/npm/web-next/next.config.js ./next.config.js
COPY client/npm/web-next/tsconfig.json ./tsconfig.json
COPY client/npm/web-next/tailwind.config.js ./tailwind.config.js
COPY client/npm/web-next/postcss.config.js ./postcss.config.js

EXPOSE 3000
CMD ["npm", "run", "start"]
