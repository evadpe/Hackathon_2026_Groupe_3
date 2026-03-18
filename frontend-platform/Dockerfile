FROM node:20-alpine

WORKDIR /app

# Installe les dépendances en premier (mise en cache Docker)
COPY frontend-platform/package*.json ./
RUN npm install

COPY frontend-platform/ .

# URL de l'API — doit être accessible depuis le navigateur (pas depuis le container)
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build

EXPOSE 3000
CMD ["npm", "start"]
