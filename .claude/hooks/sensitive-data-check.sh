#!/usr/bin/env bash
# This project was developed with assistance from AI tools.
#
# sensitive-data-check.sh — Scan for potential sensitive data patterns
#
# This script checks text input for patterns that may indicate sensitive data
# (credentials, internal hostnames, PII) that should not be sent to AI tools.
#
# USAGE:
#   As a standalone check:
#     echo "some text" | .claude/hooks/sensitive-data-check.sh
#
#   As a Claude Code pre-tool hook (in .claude/settings.json):
#     {
#       "hooks": {
#         "PreToolUse": [
#           {
#             "matcher": ".*",
#             "command": ".claude/hooks/sensitive-data-check.sh"
#           }
#         ]
#       }
#     }
#
# BEHAVIOR:
#   - Reads from stdin
#   - Checks for common sensitive data patterns
#   - Exits 0 (success) if no patterns found
#   - Exits 1 with a warning message if patterns are detected
#
# CUSTOMIZATION:
#   - Add project-specific patterns to the CUSTOM_PATTERNS array below
#   - Adjust the internal hostname patterns for your organization

set -uo pipefail

# Read input from stdin
INPUT=$(cat)

WARNINGS=()

# Helper: grep wrapper that won't exit on no-match (grep returns 1 on no match)
check_pattern() {
    echo "$INPUT" | grep "$@" >/dev/null 2>&1
}

# --- AWS Keys ---
if check_pattern -qE -- 'AKIA[0-9A-Z]{16}'; then
    WARNINGS+=("Possible AWS Access Key ID detected (AKIA...)")
fi

# --- AWS Secret Keys ---
if check_pattern -qE -- '[A-Za-z0-9/+=]{40}' && check_pattern -qiE -- '(aws|secret|key)'; then
    WARNINGS+=("Possible AWS Secret Access Key detected")
fi

# --- Generic API keys/tokens ---
if check_pattern -qiE -- '(api[_-]?key|api[_-]?token|access[_-]?token|auth[_-]?token|secret[_-]?key)[[:space:]]*[=:][[:space:]]*['"'"'"][A-Za-z0-9_\-]{20,}'; then
    WARNINGS+=("Possible API key or token assignment detected")
fi

# --- Private keys ---
if check_pattern -qE -- 'BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY'; then
    WARNINGS+=("Private key block detected")
fi

# --- Red Hat internal hostnames ---
if check_pattern -qiE -- '[a-zA-Z0-9._-]+\.(corp\.redhat\.com|redhat\.com|stage\.redhat\.com|int\.redhat\.com)'; then
    WARNINGS+=("Red Hat internal hostname detected — use a placeholder instead")
fi

# --- Internal IP ranges (common RFC 1918) ---
if check_pattern -qE -- '(10\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}|172\.(1[6-9]|2[0-9]|3[01])\.[0-9]{1,3}\.[0-9]{1,3}|192\.168\.[0-9]{1,3}\.[0-9]{1,3})'; then
    WARNINGS+=("Internal IP address detected — consider using a placeholder")
fi

# --- Email addresses (potential PII) ---
if check_pattern -qiE -- '[a-zA-Z0-9._%+-]+@redhat\.com'; then
    WARNINGS+=("Red Hat email address detected — consider if this is necessary")
fi

# --- Password patterns ---
if check_pattern -qiE -- '(password|passwd|pwd)[[:space:]]*[=:][[:space:]]*['"'"'"][^'"'"'"]{4,}'; then
    WARNINGS+=("Possible password assignment detected")
fi

# --- Connection strings ---
if check_pattern -qiE -- '(mongodb|postgres|mysql|redis|amqp|jdbc)://[^[:space:]]+@'; then
    WARNINGS+=("Database/service connection string with credentials detected")
fi

# --- GitHub/GitLab tokens ---
if check_pattern -qE -- '(ghp_[A-Za-z0-9]{36}|glpat-[A-Za-z0-9\-]{20,})'; then
    WARNINGS+=("GitHub/GitLab personal access token detected")
fi

# --- Custom patterns (add your own below) ---
# CUSTOM_PATTERNS=(
#     'pattern1:Description of what was found'
#     'pattern2:Description of what was found'
# )
# for entry in "${CUSTOM_PATTERNS[@]}"; do
#     pattern="${entry%%:*}"
#     description="${entry#*:}"
#     if echo "$INPUT" | grep -qE "$pattern"; then
#         WARNINGS+=("$description")
#     fi
# done

# --- Report results ---
if [ ${#WARNINGS[@]} -gt 0 ]; then
    echo "WARNING: Potential sensitive data detected in input:"
    echo ""
    for warning in "${WARNINGS[@]}"; do
        echo "  - $warning"
    done
    echo ""
    echo "Red Hat AI policy prohibits sending confidential data, PII, credentials,"
    echo "or internal infrastructure details to AI tools. Please review and remove"
    echo "sensitive content before proceeding."
    echo ""
    echo "See .claude/rules/ai-compliance.md for full policy details."
    exit 1
fi

exit 0
