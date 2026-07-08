# Production frontend image: multi-stage build.
#   Stage 1 (build): node:20-alpine -> npm install + npm run build -> /app/dist
#   Stage 2 (serve): nginx:alpine serves the static SPA on :80 and proxies
#                    /api/ -> backend:8000 (see nginx.conf).
#
# NOTE: for local development we do NOT use this image. docker-compose.yml runs
# the Vite dev server directly from a node image (see that file). This Dockerfile
# is the production artifact referenced by docker-compose.prod.yml.

# ---- Stage 1: build the SPA ----
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .
RUN npm run build

# ---- Stage 2: serve with nginx ----
FROM nginx:alpine

# Replace the default site config with our SPA + /api proxy config.
RUN rm -f /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
