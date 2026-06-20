FROM m.daocloud.io/docker.io/library/node:21-slim AS builder
WORKDIR /app
COPY package*.json ./
RUN npm config set registry https://registry.npmmirror.com && npm ci
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM m.daocloud.io/docker.io/library/node:21-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
CMD ["node", "server.js"]
