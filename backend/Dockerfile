FROM node:20-bullseye-slim

RUN apt-get update && apt-get install -y \
    python3 \
    make \
    g++ \
    libreoffice \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package*.json ./

# Usiamo lo stesso flag anche qui
RUN npm install --legacy-peer-deps && npm cache clean --force

COPY . .

CMD ["npm", "run", "dev"]