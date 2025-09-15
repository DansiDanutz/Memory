# Memory App Frontend - Production Docker Image
FROM node:18-alpine as builder

# Build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

# Labels
LABEL org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.name="Memory App Frontend" \
      org.label-schema.description="Digital Immortality Platform Web Interface" \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.version=$VERSION

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy application code
COPY . .

# Build the application
RUN npm run build || echo "No build script"

# Production stage
FROM node:18-alpine

# Install dumb-init to handle signals properly
RUN apk add --no-cache dumb-init

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001

# Set working directory
WORKDIR /app

# Copy from builder
COPY --from=builder --chown=nodejs:nodejs /app .

# Switch to non-root user
USER nodejs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD node -e "require('http').get('http://localhost:5000/health', (r) => {r.statusCode === 200 ? process.exit(0) : process.exit(1)})"

# Environment variables
ENV NODE_ENV=production \
    PORT=5000

# Expose port
EXPOSE 5000

# Use dumb-init to run node
ENTRYPOINT ["dumb-init", "--"]
CMD ["node", "server.js"]