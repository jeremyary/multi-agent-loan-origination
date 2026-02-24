#!/bin/bash
# This project was developed with assistance from AI tools.
#
# Deploy application via Helm to OpenShift.
#
# Usage: scripts/deploy.sh [extra-helm-set-args...]
#
# Env vars (set by Makefile exports):
#   PROJECT_NAME    -- helm release name (default: summit-cap)
#   NAMESPACE       -- OpenShift namespace (default: summit-cap)
#   ENV_FILE        -- env file to source (default: .env)
#   IMAGE_TAG       -- image tag (default: latest)
#   REGISTRY        -- registry host (default: quay.io)
#   REGISTRY_NS     -- registry namespace/org (default: summit-cap)
#   HELM_TIMEOUT    -- helm timeout (default: 15m)
#   HELM_EXTRA_ARGS -- additional helm args (default: empty)
set -euo pipefail

PROJECT_NAME="${PROJECT_NAME:-summit-cap}"
NAMESPACE="${NAMESPACE:-$PROJECT_NAME}"
ENV_FILE="${ENV_FILE:-.env}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
REGISTRY="${REGISTRY:-quay.io}"
REGISTRY_NS="${REGISTRY_NS:-$PROJECT_NAME}"
HELM_TIMEOUT="${HELM_TIMEOUT:-15m}"
HELM_EXTRA_ARGS="${HELM_EXTRA_ARGS:-}"

# Load .env file if present
if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi

# Resolve cluster domain for routes
CLUSTER_DOMAIN="${CLUSTER_DOMAIN:-}"
if [ -z "$CLUSTER_DOMAIN" ]; then
    CLUSTER_DOMAIN=$(oc whoami --show-server 2>/dev/null \
        | sed -E 's|https://api\.([^:]+).*|apps.\1|' || echo "")
fi

echo "Registry:  $REGISTRY/$REGISTRY_NS"
echo "Namespace: $NAMESPACE"

helm upgrade --install "$PROJECT_NAME" "./deploy/helm/$PROJECT_NAME" \
    --namespace "$NAMESPACE" \
    --timeout "$HELM_TIMEOUT" \
    --wait \
    --wait-for-jobs \
    --set global.imageRegistry="$REGISTRY" \
    --set global.imageRepository="$REGISTRY_NS" \
    --set global.imageTag="$IMAGE_TAG" \
    --set routes.sharedHost="$PROJECT_NAME-$NAMESPACE.$CLUSTER_DOMAIN" \
    --set secrets.POSTGRES_DB="${POSTGRES_DB:-}" \
    --set secrets.POSTGRES_USER="${POSTGRES_USER:-}" \
    --set secrets.POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}" \
    --set secrets.DATABASE_URL="${DATABASE_URL:-}" \
    --set secrets.DEBUG="${DEBUG:-}" \
    --set secrets.ALLOWED_HOSTS="${ALLOWED_HOSTS:-}" \
    --set secrets.VITE_API_BASE_URL="${VITE_API_BASE_URL:-}" \
    --set secrets.VITE_ENVIRONMENT="${VITE_ENVIRONMENT:-}" \
    "$@" \
    $HELM_EXTRA_ARGS \
    || {
        echo ""
        echo "Helm deployment failed!"
        echo ""
        echo "Run 'make debug' for diagnostics or 'make status' for quick status."
        exit 1
    }

echo "Deployment successful"
