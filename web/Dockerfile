FROM node:22 AS build
WORKDIR /build
COPY package.json ./
RUN npm install --no-audit --no-fund
COPY tailwind.config.js ./
COPY src ./src
COPY public ./public
RUN npx tailwindcss -c tailwind.config.js -i src/app.css -o public/css/app.css --minify \
 && mkdir -p public/vendor \
 && cp node_modules/marked/lib/marked.esm.js public/vendor/marked.esm.js

FROM nginx:1.27
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /build/public /usr/share/nginx/html
