# NOTE: Multi-stage builds require Docker v17.05 or later.

# create the build environment
FROM node:8.16.2-alpine AS build
WORKDIR /app
ENV PATH /app/node_modules/.bin:$PATH
RUN npm install react-scripts@3.2.0 -g
COPY package.json /app/package.json
RUN npm install
COPY . /app/
ARG ENABLE_TESTS
RUN if [ -n "$ENABLE_TESTS" ]; then echo -e "\nREACT_APP_TEST_MODE=1" >>/app/.env ; fi
RUN npm run build

# create the final target image
FROM nginx:1.17.5-alpine
COPY docker/nginx-default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build /usr/share/nginx/html
EXPOSE 80
CMD [ "nginx", "-g", "daemon off;" ]
