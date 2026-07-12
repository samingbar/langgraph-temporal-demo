FROM nginx:1.27-alpine

ENV WEB_PORT=8080 \
    DEFAULT_AGENT_BACKEND=temporal-langgraph \
    TEMPORAL_LANGGRAPH_BACKEND_URL=http://localhost:8002 \
    TEMPORAL_UI_URL=http://localhost:8233

COPY web/ /usr/share/nginx/html/
COPY docker/web-entrypoint.sh /docker-entrypoint.d/40-generate-web-config.sh
COPY docker/nginx-default.conf.template /etc/nginx/templates/default.conf.template
RUN chmod +x /docker-entrypoint.d/40-generate-web-config.sh

EXPOSE 8080
