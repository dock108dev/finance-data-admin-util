FROM node:20-slim

WORKDIR /app

# Install dependencies (cache layer)
COPY web/package.json web/package-lock.json* ./
RUN npm ci

# Application code
COPY web/ .

# Build with the API_URL baked in for Docker networking
ARG API_URL=http://fin-api:8000
ENV API_URL=${API_URL}
RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
