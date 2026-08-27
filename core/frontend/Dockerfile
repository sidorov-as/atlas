FROM node:22-slim AS dependencies

WORKDIR /app
COPY package.json package-lock.json .npmrc ./
COPY core/frontend/package.json core/frontend/package.json
COPY plugin-api/typescript/package.json plugin-api/typescript/package.json
COPY plugins/standard-catalog/frontend/package.json plugins/standard-catalog/frontend/package.json
COPY plugins/apis/frontend/package.json plugins/apis/frontend/package.json
COPY plugins/c4/frontend/package.json plugins/c4/frontend/package.json
COPY plugins/database-schema/frontend/package.json plugins/database-schema/frontend/package.json
COPY plugins/flows/frontend/package.json plugins/flows/frontend/package.json
RUN npm ci

FROM dependencies AS build
COPY . .
RUN npm run build --workspace=frontend

FROM dependencies AS development
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--workspace=frontend", "--", "--host"]

FROM caddy:2-alpine AS production
COPY core/frontend/docker/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/core/frontend/dist /usr/share/caddy
EXPOSE 80
