FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y chrony
RUN echo "pool pool.ntp.org iburst" >> /etc/chrony/chrony.conf
USER chrony
