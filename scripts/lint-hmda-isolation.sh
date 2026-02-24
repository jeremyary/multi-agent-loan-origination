#!/bin/bash
# This project was developed with assistance from AI tools.
#
# Detect HMDA isolation violations:
# 1. References to "hmda" schema outside services/compliance/
# 2. Imports of compliance pool outside services/compliance/
#
# Excludes: test files, migration files, config, this script, db models,
#           db __init__.py (exports), compose.yml, .env files
set -euo pipefail

VIOLATIONS=0
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "Checking HMDA isolation boundaries..."

# Pattern 1: Direct references to hmda schema in Python code outside allowed paths
# Catches: schema="hmda", schema='hmda', "hmda.demographics", hmda.demographics
# Excludes: route registrations (prefix="/api/hmda"), module imports (routes.hmda)
HMDA_REFS=$(grep -rn --include="*.py" \
    -e 'schema.*=.*"hmda"' \
    -e 'schema.*=.*'"'"'hmda'"'"'' \
    -e '"hmda\.demographics' \
    "$ROOT_DIR/packages/api/src/" \
    2>/dev/null \
    | grep -v "services/compliance/" \
    | grep -v "__pycache__" \
    || true)

if [ -n "$HMDA_REFS" ]; then
    echo ""
    echo "VIOLATION: HMDA schema references found outside services/compliance/:"
    echo "$HMDA_REFS"
    VIOLATIONS=$((VIOLATIONS + 1))
fi

# Pattern 2: Imports of get_compliance_db or ComplianceSessionLocal outside allowed paths
COMPLIANCE_IMPORTS=$(grep -rn --include="*.py" \
    -e "get_compliance_db" \
    -e "ComplianceSessionLocal" \
    -e "compliance_engine" \
    "$ROOT_DIR/packages/api/src/" \
    2>/dev/null \
    | grep -v "services/compliance/" \
    | grep -v "routes/hmda.py" \
    | grep -v "__pycache__" \
    || true)

if [ -n "$COMPLIANCE_IMPORTS" ]; then
    echo ""
    echo "VIOLATION: Compliance pool imports found outside allowed paths:"
    echo "$COMPLIANCE_IMPORTS"
    VIOLATIONS=$((VIOLATIONS + 1))
fi

# Pattern 3: Direct import of HmdaDemographic outside allowed paths
HMDA_MODEL_IMPORTS=$(grep -rn --include="*.py" \
    -e "HmdaDemographic" \
    "$ROOT_DIR/packages/api/src/" \
    2>/dev/null \
    | grep -v "services/compliance/" \
    | grep -v "__pycache__" \
    || true)

if [ -n "$HMDA_MODEL_IMPORTS" ]; then
    echo ""
    echo "VIOLATION: HmdaDemographic model imported outside services/compliance/:"
    echo "$HMDA_MODEL_IMPORTS"
    VIOLATIONS=$((VIOLATIONS + 1))
fi

if [ "$VIOLATIONS" -gt 0 ]; then
    echo ""
    echo "Found $VIOLATIONS HMDA isolation violation(s)."
    echo "HMDA data access must go through services/compliance/ only."
    exit 1
fi

echo "HMDA isolation check passed."
exit 0
