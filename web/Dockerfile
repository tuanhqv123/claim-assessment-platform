# Frontend: Next.js 16 (standalone output). Multi-stage: build, then a slim runner.
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# API base is same-origin (Caddy proxies /api -> backend), so build with an
# empty NEXT_PUBLIC_API_URL -> the client calls relative "/api/..." paths.
ENV NEXT_PUBLIC_API_URL=""
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
# Standalone server + static assets + public files.
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
