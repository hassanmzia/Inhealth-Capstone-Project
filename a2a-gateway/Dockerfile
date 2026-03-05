# Stage 1: development
FROM node:20-alpine AS development

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install && npm install -g nodemon ts-node typescript

COPY . .

EXPOSE 3002

CMD ["npx", "ts-node-dev", "--respawn", "--transpile-only", "src/index.ts"]

# Stage 2: builder (compile TypeScript)
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

# Stage 3: production
FROM node:20-alpine AS production

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --omit=dev

COPY --from=builder /app/dist ./dist

EXPOSE 3002

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD wget -qO- http://localhost:3002/health || exit 1

CMD ["node", "dist/index.js"]
