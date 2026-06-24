# ── Development stage ─────────────────────────────────────────────────────────
FROM node:20-bullseye-slim AS development

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 make g++ curl libreoffice \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package*.json ./
RUN npm install --legacy-peer-deps

COPY . .

EXPOSE 3001
CMD ["npm", "run", "dev"]

# ── Build stage ───────────────────────────────────────────────────────────────
FROM development AS builder

RUN npm run build

# ── Production stage ──────────────────────────────────────────────────────────
FROM node:20-bullseye-slim AS production

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 libreoffice curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package*.json ./
RUN npm install --legacy-peer-deps --omit=dev

COPY --from=builder /app/dist ./dist

ENV NODE_ENV=production

EXPOSE 3001
CMD ["node", "dist/index.js"]
