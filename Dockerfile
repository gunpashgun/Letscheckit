# Используем официальный Node.js образ с ffmpeg
FROM apify/actor-node:18

# Устанавливаем ffmpeg для обработки видео
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Копируем package files
COPY package*.json ./

# Устанавливаем зависимости
RUN npm install --production

# Копируем исходный код
COPY . ./

# Запускаем актора
CMD ["npm", "start"]

