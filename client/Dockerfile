FROM node:22-slim

WORKDIR /app

# 의존성을 먼저 설치해 레이어 캐시를 살린다
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev"]
