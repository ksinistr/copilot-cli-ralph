FROM node:22-slim

# Install Python and required system dependencies
RUN apt-get update && \
    apt-get install -y python3 curl git bash && \
    rm -rf /var/lib/apt/lists/*

# Map 'python' command to 'python3' so our ENTRYPOINT works correctly
RUN ln -s /usr/bin/python3 /usr/bin/python

# Install the correct GitHub Copilot CLI package
RUN npm install -g @github/copilot

ARG GH_TOKEN
ENV GH_TOKEN=${GH_TOKEN}

WORKDIR /workspace
COPY loop.py .

CMD ["python", "loop.py"]
