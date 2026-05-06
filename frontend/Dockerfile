FROM node:20-bullseye-slim

RUN apt-get update && apt-get install -y \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package*.json ./

# Il flag magico per risolvere il tuo errore ERESOLVE
RUN npm install --legacy-peer-deps

COPY . .

CMD ["npm", "run", "dev"]