# Используем официальный Node.js образ с ffmpeg
FROM apify/actor-node:18

# Устанавливаем ffmpeg для обработки видео (Alpine Linux использует apk)
RUN apk add --no-cache ffmpeg

# Копируем package files
COPY package*.json ./

# Устанавливаем зависимости
RUN npm install --production

# Копируем исходный код
COPY . ./

# Запускаем актора
CMD ["npm", "start"]

