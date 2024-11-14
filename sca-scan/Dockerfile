FROM python:3.11-slim

LABEL maintainer="Steve Christiaens<schristiaens@bamboohr.com>"
LABEL version="0.1"
LABEL description="An image for an SCA scanning tool."

WORKDIR /scan


RUN apt-get update && \
    apt-get install -y git nodejs npm && \
    npm install -g @cyclonedx/cdxgen && \
    python3 -m pip install semgrep

COPY ./src /app

ENTRYPOINT ["/app/scan.sh"]