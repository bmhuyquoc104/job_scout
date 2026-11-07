FROM node:26-alpine
# Node 26 images ship without corepack, so pnpm is installed once here instead of on every start.
RUN npm install -g pnpm@12.16.1
WORKDIR /app
CMD ["sh", "-c", "pnpm install --frozen-lockfile && pnpm dev --host 0.0.0.0"]
