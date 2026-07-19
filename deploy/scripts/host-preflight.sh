#!/usr/bin/env bash
# Host preflight for explorer production compose (/opt/explorer on the VPS).
# Usage: host-preflight.sh [DEPLOY_DIR]
# Exit 0 if ready for docker compose pull/up; nonzero with a clear message otherwise.
set -euo pipefail

DEPLOY_DIR="${1:-/opt/explorer}"
COMPOSE_FILE="${DEPLOY_DIR}/compose.prod.yml"
ENV_FILE="${DEPLOY_DIR}/.env.prod"
# Must match top-level `name:` in compose.prod.yml
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-explorer}"

fail() {
  echo "error: $*" >&2
  exit 1
}

# True if assignment lines still use the example placeholder (comments ignored).
env_has_placeholder_secrets() {
  local file="$1"
  grep -qE '^[A-Za-z_][A-Za-z0-9_]*=CHANGE_ME([[:space:]]|$)' "$file"
}

# True if a container (by id) belongs to this compose project.
container_in_project() {
  local cid="$1"
  local project="$2"
  local label
  label="$(docker inspect -f '{{index .Config.Labels "com.docker.compose.project"}}' "${cid}" 2>/dev/null || true)"
  [ -n "${label}" ] && [ "${label}" = "${project}" ]
}

# Fail unless host port is free, or already bound by this compose project.
check_host_port() {
  local port="$1"
  local project="$2"
  local cid name
  local found=0

  while read -r cid; do
    [ -z "${cid}" ] && continue
    found=1
    if container_in_project "${cid}" "${project}"; then
      continue
    fi
    name="$(docker inspect -f '{{.Name}}' "${cid}" 2>/dev/null || echo unknown)"
    fail "host port ${port} is used by container ${cid} (${name}), not compose project '${project}' — stop it first"
  done < <(docker ps --filter "publish=${port}" --format '{{.ID}}' 2>/dev/null || true)

  if [ "${found}" -eq 1 ]; then
    return 0
  fi

  if command -v ss >/dev/null 2>&1; then
    if ss -tlnH 2>/dev/null | awk '{print $4}' | grep -Eq "[:.]${port}\$"; then
      fail "host port ${port} is already in use (not by compose project '${project}'). Free it: ss -tlnp | grep :${port}"
    fi
  fi
}

main() {
  [ -d "${DEPLOY_DIR}" ] || fail "${DEPLOY_DIR} missing. As root: mkdir -p ${DEPLOY_DIR} && chown \${USER}:\${USER} ${DEPLOY_DIR}"
  [ -w "${DEPLOY_DIR}" ] || fail "${DEPLOY_DIR} not writable by ${USER}. As root: chown -R ${USER}:${USER} ${DEPLOY_DIR}"
  [ -f "${ENV_FILE}" ] || fail "${ENV_FILE} missing (copy from .env.prod.example and set secrets)"
  [ -f "${COMPOSE_FILE}" ] || fail "${COMPOSE_FILE} missing"

  if env_has_placeholder_secrets "${ENV_FILE}"; then
    fail "${ENV_FILE} still has KEY=CHANGE_ME placeholders — set POSTGRES_PASSWORD and CYBERYEN_RPC_PASSWORD"
  fi

  command -v docker >/dev/null || fail "docker not installed or not on PATH for ${USER}"
  docker info >/dev/null 2>&1 || fail "cannot talk to Docker daemon (add ${USER} to the docker group?)"
  docker compose version >/dev/null 2>&1 || fail "docker compose plugin missing"
  mkdir -p "${DEPLOY_DIR}/nginx"

  check_host_port 58383 "${COMPOSE_PROJECT_NAME}"
  check_host_port 44551 "${COMPOSE_PROJECT_NAME}"
  check_host_port 80 "${COMPOSE_PROJECT_NAME}"
  check_host_port 443 "${COMPOSE_PROJECT_NAME}"

  echo "host preflight ok (${DEPLOY_DIR}, project=${COMPOSE_PROJECT_NAME})"
}

# Sourced by unit tests (skip main).
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
