#!/usr/bin/env bash
# Local unit tests for host-preflight helpers (no Docker required).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=host-preflight.sh
source "${ROOT}/deploy/scripts/host-preflight.sh"

fail_test() {
  echo "FAIL: $*" >&2
  exit 1
}

tmpdir="$(mktemp -d)"
trap 'rm -rf "${tmpdir}"' EXIT

# --- env_has_placeholder_secrets ---
cat >"${tmpdir}/ok.env" <<'E'
# replace every CHANGE_ME value
POSTGRES_PASSWORD=s3cret
CYBERYEN_RPC_PASSWORD=also_secret
E
env_has_placeholder_secrets "${tmpdir}/ok.env" && fail_test "ok.env should not flag placeholders"

cat >"${tmpdir}/bad.env" <<'E'
# replace every CHANGE_ME value
POSTGRES_PASSWORD=CHANGE_ME
CYBERYEN_RPC_PASSWORD=real
E
env_has_placeholder_secrets "${tmpdir}/bad.env" || fail_test "bad.env should flag POSTGRES_PASSWORD=CHANGE_ME"

cat >"${tmpdir}/comment_only.env" <<'E'
# Copy and replace every CHANGE_ME value.
POSTGRES_PASSWORD=real
CYBERYEN_RPC_PASSWORD=real
E
env_has_placeholder_secrets "${tmpdir}/comment_only.env" && fail_test "comment-only CHANGE_ME must not fail"

# --- container_in_project matching (mock docker inspect) ---
docker() {
  if [ "$1" = "inspect" ]; then
    # last arg is container id
    local id="${*: -1}"
    case "${id}" in
      ourshort | ourfull0123456789abcdef) echo "explorer" ;;
      other) echo "otherproj" ;;
      *) echo "" ;;
    esac
    return 0
  fi
  return 1
}
export -f docker

container_in_project "ourshort" "explorer" || fail_test "short id of our project should match"
container_in_project "ourfull0123456789abcdef" "explorer" || fail_test "full id of our project should match"
container_in_project "other" "explorer" && fail_test "other project should not match"
container_in_project "unknown" "explorer" && fail_test "missing label should not match"

echo "ok: deploy/scripts/test_host_preflight.sh"
