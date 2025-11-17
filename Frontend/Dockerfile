FROM node:20-alpine AS build

WORKDIR /app
ENV NODE_ENV=production

ARG VITE_API_BASE_URL=https://api-alpha-hak-copilot.ruka.me/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

FROM nginx:1.27-alpine AS production

RUN apk add --no-cache curl

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s CMD curl -f http://localhost/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]
