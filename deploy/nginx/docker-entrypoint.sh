#!/bin/sh
# Select HTTP-only vs TLS nginx configs based on cert presence.
# Certs absent → HTTP serves traffic (nginx -t must pass).
# Certs present → HTTPS + HTTP→HTTPS redirect (ACME challenge stays on :80).
set -eu

CONF_D="${NGINX_CONF_D:-/etc/nginx/conf.d}"
TEMPLATES="${NGINX_TEMPLATES:-/etc/nginx/templates}"
CERT_DIR="${NGINX_CERTS:-/etc/nginx/certs}"

mkdir -p /var/cache/nginx/api /var/www/certbot "$CERT_DIR" "$CONF_D"

# Drop the distro default server so our templates own :80/:443.
rm -f "$CONF_D/default.conf" "$CONF_D/00-http.conf" "$CONF_D/10-https.conf"

if [ -f "$CERT_DIR/fullchain.pem" ] && [ -f "$CERT_DIR/privkey.pem" ]; then
    echo "nginx-entrypoint: TLS certs found — enabling HTTPS + HTTP redirect"
    cp "$TEMPLATES/http-redirect.conf" "$CONF_D/00-http.conf"
    cp "$TEMPLATES/https.conf" "$CONF_D/10-https.conf"
else
    echo "nginx-entrypoint: TLS certs absent — HTTP-only mode"
    cp "$TEMPLATES/http-only.conf" "$CONF_D/00-http.conf"
fi

exec "$@"
