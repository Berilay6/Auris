# syntax=docker/dockerfile:1
# ============================================================================
# auris-frontend — AS1 Presentation (HLD §3.3.1)
# Build context: ./frontend  (docker-compose.yml → auris-frontend.build)
#
# Two stages:
#   1) build   : Node compiles the React app → /app/dist (static files)
#   2) runtime : Nginx + dist only. Node, node_modules and the source code
#                are NOT in the final image (smaller image, smaller attack surface).
# ============================================================================

# ---------------------------------------------------------------------------
# 1) Build stage
# ---------------------------------------------------------------------------
FROM node:22-alpine AS build

WORKDIR /app

# Dependency manifests first: when only the source changes, this layer
# comes from cache and "npm ci" does not run again.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Vite inlines VITE_-prefixed env vars at BUILD time
# (import.meta.env.VITE_POLL_INTERVAL_MS). They cannot be changed at runtime;
# rebuild the image to change the value.
# Compose passes it from POLL_INTERVAL_MS in .env (HLD §3.6.1: ~3 s).
ARG VITE_POLL_INTERVAL_MS=3000
ENV VITE_POLL_INTERVAL_MS=${VITE_POLL_INTERVAL_MS}

RUN npm run build

# ---------------------------------------------------------------------------
# 2) Runtime stage
# ---------------------------------------------------------------------------
# alpine: the compose healthcheck uses "wget", which BusyBox ships on alpine.
FROM nginx:1.28-alpine AS runtime

# Replace the official image's default site config with ours.
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

# CMD comes from the official image: nginx -g "daemon off;"
