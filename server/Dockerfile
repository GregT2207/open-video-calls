FROM rust:1.67

ENV SERVER_ADDRESS=127.0.0.1
ENV SERVER_PORT=5000

WORKDIR /usr/src/open-video-calls/server

COPY . .

RUN cargo install --path .

EXPOSE 5000/udp

CMD open-video-calls-server