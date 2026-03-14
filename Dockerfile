FROM golang:1.24-bookworm AS builder

WORKDIR /src

COPY go.mod ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /out/loop ./main.go

FROM debian:bookworm-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends bash ca-certificates curl git && \
    rm -rf /var/lib/apt/lists/* && \
    curl -fsSL https://gh.io/copilot-install | bash

WORKDIR /workspace

COPY --from=builder /out/loop /usr/local/bin/loop
COPY --from=builder /usr/local/go /usr/local/go

ENV PATH="/usr/local/go/bin:${PATH}"
ENV GOPATH="/root/go"

ENTRYPOINT ["/usr/local/bin/loop"]
