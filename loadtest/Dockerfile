FROM python:3.12-slim

WORKDIR /loadtest

RUN pip install --no-cache-dir locust

# locustfile is mounted via docker-compose volume

EXPOSE 8089

CMD ["locust", "--version"]

