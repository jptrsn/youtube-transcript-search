FROM node:22-alpine AS builder

WORKDIR /build

# Copy root .env.prod and rename it to what Vite expects in production mode
COPY .env.prod ./.env.production

# Copy frontend package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci

# Copy frontend source
COPY frontend/ ./

# Set NODE_ENV so Vite knows to look for .env.production
ENV NODE_ENV=production

# Build the app (Vite will read from .env.production)
RUN npm run build

# Production stage
FROM node:22-alpine

WORKDIR /app

# Copy built app
COPY --from=builder /build/build ./build
COPY --from=builder /build/package*.json ./
COPY --from=builder /build/node_modules ./node_modules

EXPOSE 3000

ENV NODE_ENV=production

CMD ["node", "build/index.js"]