# ==============================================================================
# Production Dockerfile for SupplyChainAgent React/Vite Frontend
# Multi-stage build: compile TypeScript/React with Node, serve with Nginx
# ==============================================================================

# Stage 1: Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy frontend source code and build
COPY frontend/ ./
RUN npm run build

# Stage 2: Production runtime stage
FROM nginx:alpine-slim

# Copy custom nginx configuration
COPY infra/docker/nginx.conf /etc/nginx/conf.d/default.conf

# Copy compiled static assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose HTTP port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
