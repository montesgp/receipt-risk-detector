# syntax=docker/dockerfile:1
#
# Production image for the receipt-risk-web frontend. Build context is the
# REPO ROOT, matching apps/api/Dockerfile's convention (Railway always builds
# from repo root regardless of dockerfilePath), so paths below are relative
# to the repo root.
#
# adapter-static (svelte.config.js) produces a fully prerendered site with no
# fallback route (strict: true) -- every path is a real file on disk, so the
# runtime stage only needs a static file server, never a Node process.

# ---- build ----
FROM node:20-slim AS build
WORKDIR /app
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci
COPY apps/web/ ./

# PUBLIC_API_BASE_URL is baked into the client bundle at build time by
# SvelteKit's $env/static/public -- it must exist as a build ARG, not just a
# runtime env var. Railway passes a service Variable of the same name through
# automatically once it's declared here (see docs/guides/dockerfiles).
ARG PUBLIC_API_BASE_URL
ENV PUBLIC_API_BASE_URL=$PUBLIC_API_BASE_URL

RUN npm run build

# ---- runtime ----
FROM node:20-slim
RUN npm install -g serve@14
WORKDIR /app
COPY --from=build /app/build ./build

EXPOSE 3000
# Shell form (not exec form) so $PORT expands -- Railway injects it at
# container start and it varies per deploy.
CMD ["sh", "-c", "serve build -l $PORT"]
