FROM node:20-alpine AS build

WORKDIR /app
COPY package.json package-lock.json* /app/
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY index.html vite.config.ts tsconfig.json tsconfig.node.json /app/
COPY public /app/public
COPY src /app/src
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
