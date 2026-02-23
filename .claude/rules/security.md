# Security Baseline

## Secrets
- Never hardcode secrets, API keys, tokens, or passwords in source code
- Use environment variables or a secrets manager
- Add `.env` files to `.gitignore`
- Rotate credentials immediately if exposed

## Input Handling
- Validate and sanitize all external input at system boundaries
- Use parameterized queries for all database operations — never string concatenation
- Encode output contextually (HTML, URL, JS) to prevent XSS
- Set appropriate Content-Security-Policy headers

## Authentication & Authorization
- Hash passwords with bcrypt/scrypt/argon2 (never MD5/SHA for passwords)
- Implement rate limiting on authentication endpoints
- Use short-lived tokens with refresh rotation
- Enforce least-privilege access on all operations

## Transport
- HTTPS only in production — enforce via HSTS headers
- Validate TLS certificates; do not disable certificate verification
- Set `Secure`, `HttpOnly`, and `SameSite` flags on cookies

## Dependencies
- Pin dependency versions in lock files
- Review new dependencies before adding (check maintenance, license, security history)
- Run dependency vulnerability scanning in CI (`npm audit`, `trivy`, etc.)

## Logging
- Log security-relevant events: authentication, authorization failures, input validation failures
- See `observability.md` for the full "What NEVER to Log" list and structured logging standards
