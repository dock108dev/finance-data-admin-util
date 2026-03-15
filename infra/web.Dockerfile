FROM node:20-slim

WORKDIR /app

# Install dependencies (cache layer)
COPY web/package.json web/package-lock.json* ./
RUN npm ci

# Application code + build
COPY web/ .
RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
