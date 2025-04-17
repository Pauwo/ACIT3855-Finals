# FROM nginx:alpine
# COPY src/ /usr/share/nginx/html/
# COPY public/ /usr/share/nginx/html/public/
# EXPOSE 80
# CMD ["nginx", "-g", "daemon off;"]

FROM nginx:alpine
COPY ./src /usr/share/nginx/html
COPY ./public /usr/share/nginx/html/public
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]