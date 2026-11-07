FROM node:26-alpine
# Node 26 images ship without corepack, so pnpm is installed once here instead of on every start.
RUN npm install -g pnpm@12.16.1
WORKDIR /app
# The named node_modules volume copies this owner on first use, so the non-root user can install.
RUN mkdir -p /app/node_modules && chown node:node /app /app/node_modules
USER node
CMD ["sh", "-c", "pnpm install --frozen-lockfile && pnpm dev --host 0.0.0.0"]
