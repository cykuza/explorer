# Cyberyen Core 0.21.6.1 (linux x86_64 release binaries)
FROM debian:bookworm-slim

ARG CYBERYEN_VERSION=0.21.6.1
ARG CYBERYEN_ARCH=x86_64-linux-gnu
ARG CYBERYEN_TARBALL=cyberyen-${CYBERYEN_VERSION}-${CYBERYEN_ARCH}.tar.gz
ARG CYBERYEN_URL=https://github.com/cyberyen/cyberyen/releases/download/v${CYBERYEN_VERSION}/${CYBERYEN_TARBALL}

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL "${CYBERYEN_URL}" -o /tmp/cyberyen.tar.gz \
    && tar -xzf /tmp/cyberyen.tar.gz -C /tmp \
    && install -m 0755 /tmp/cyberyen-${CYBERYEN_VERSION}/bin/cyberyend /usr/local/bin/cyberyend \
    && install -m 0755 /tmp/cyberyen-${CYBERYEN_VERSION}/bin/cyberyen-cli /usr/local/bin/cyberyen-cli \
    && rm -rf /tmp/cyberyen.tar.gz /tmp/cyberyen-${CYBERYEN_VERSION} \
    && apt-get purge -y --auto-remove curl \
    && useradd --system --create-home --home-dir /data --shell /usr/sbin/nologin cyberyen \
    && mkdir -p /data \
    && chown -R cyberyen:cyberyen /data

USER cyberyen
WORKDIR /data
VOLUME ["/data"]
EXPOSE 18440 18443 28332 28333

ENTRYPOINT ["cyberyend"]
