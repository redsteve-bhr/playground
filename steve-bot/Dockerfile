FROM python:3.11-slim

LABEL maintainer="Steve Christiaens<schristiaens@bamboohr.com>"
LABEL version="0.1"
LABEL description="Slack personal assistant bot"

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY ./src .

# Default to running the local development server
CMD ["python", "local_server.py"]