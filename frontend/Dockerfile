FROM node:22-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build argument for API URL
ARG PUBLIC_API_URL=http://localhost:8000

# Set as environment variable for the build process
ENV PUBLIC_API_URL=$PUBLIC_API_URL

# Build the app - this bakes PUBLIC_API_URL into the client bundle
RUN npm run build

# Production stage
FROM node:22-alpine

WORKDIR /app

# Copy everything needed for production
COPY --from=builder /app/build ./build
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/node_modules ./node_modules

EXPOSE 3000

ENV NODE_ENV=production

CMD ["node", "build/index.js"]