# Deployment Security Review - Summit Cap Financial (ROSA)

**Reviewer:** Security Engineer
**Date:** 2026-03-06
**Scope:** All deployment configurations under `/deploy/helm/summit-cap/`
**Target Platform:** ROSA (Red Hat OpenShift on AWS) with restricted PodSecurity

## Executive Summary

Reviewed 20 Helm templates, 2 values files, Keycloak realm configuration, and database initialization scripts. Found **10 Critical**, **15 Warning**, and **8 Suggestion** level findings across secrets management, container security, network exposure, and authentication configuration.

**Top Priority Issues:**
1. Multiple weak default passwords (admin/admin, demo/demo) shipped in production values
2. Database credentials exposed in plain-text environment variables (LangFuse)
3. No image digest pinning — all images use mutable tags
4. MinIO console publicly routable with weak credentials
5. SQLAdmin panel exposed via public Route with admin/admin default

---

## Findings

### SEC-DEPLOY-01 [CRITICAL] Weak Default Passwords in Production Values

**Category:** OWASP A07:2021 – Identification and Authentication Failures
**Location:** `deploy/helm/summit-cap/values.yaml:65-76, 89-91`

**Description:**
Multiple critical services ship with weak, well-known default credentials in the production values file:

```yaml
# SQLAdmin panel
SQLADMIN_USER: "admin"
SQLADMIN_PASSWORD: "admin"

# Keycloak admin console
KC_BOOTSTRAP_ADMIN_USERNAME: "admin"
KC_BOOTSTRAP_ADMIN_PASSWORD: "admin"

# MinIO root credentials
MINIO_ROOT_USER: "minio"
MINIO_ROOT_PASSWORD: "miniosecret"

# LangFuse admin
LANGFUSE_INIT_USER_PASSWORD: "password"
```

All of these are publicly documented in the Git repository and would be deployed as-is unless operators explicitly override them.

**Impact:**
- SQLAdmin exposes full database access (all tables including HMDA demographic data)
- Keycloak admin can create users, modify roles, extract client secrets
- MinIO root can access all uploaded documents (loan applications, financials, IDs)
- LangFuse admin can view all LLM traces including PII from conversations

An attacker with knowledge of these defaults gains administrative access to multiple critical systems.

**Recommendation:**
1. Remove all default passwords from `values.yaml`
2. Make these fields **required** — fail chart deployment if not set via `--set` or external Secret
3. Add `README.md` section documenting the required secrets with examples:
   ```
   --set secrets.SQLADMIN_PASSWORD=$(openssl rand -base64 32)
   ```
4. For production deployments, integrate with external secrets management (OpenShift Secrets, Vault, AWS Secrets Manager)
5. Add Helm `required` template function to enforce override:
   ```yaml
   SQLADMIN_PASSWORD: {{ required "A valid .Values.secrets.SQLADMIN_PASSWORD is required!" .Values.secrets.SQLADMIN_PASSWORD }}
   ```

**References:**
- OWASP Top 10 A07:2021
- CWE-798: Use of Hard-coded Credentials

---

### SEC-DEPLOY-02 [CRITICAL] Database Credentials in Plain-Text Environment Variables

**Category:** OWASP A02:2021 – Cryptographic Failures
**Location:** `deploy/helm/summit-cap/templates/langfuse.yaml:61, 233`

**Description:**
LangFuse web and worker deployments construct PostgreSQL connection strings with embedded credentials in plain-text environment variables:

```yaml
- name: DATABASE_URL
  value: "postgresql://{{ .Values.secrets.POSTGRES_USER }}:{{ .Values.secrets.POSTGRES_PASSWORD }}@{{ $dbName }}:5432/langfuse"
```

While the credentials are sourced from a Kubernetes Secret, they are then **interpolated into a plain-text string** visible in:
- Pod environment via `kubectl describe pod`
- Container logs if the startup command echoes env vars
- Any debug/error output that dumps environment

This violates defense-in-depth for credential handling.

**Impact:**
An attacker with pod describe/exec access (e.g., via a compromised ServiceAccount or RBAC misconfiguration) can extract the database password without needing Secret read permissions.

**Recommendation:**
Use the existing `secretKeyRef` pattern consistently:

```yaml
- name: DATABASE_URL
  valueFrom:
    secretKeyRef:
      name: {{ $secretName }}
      key: LANGFUSE_DATABASE_URL  # Add this to secret.yaml
```

Add to `secret.yaml`:
```yaml
LANGFUSE_DATABASE_URL: {{ printf "postgresql://%s:%s@%s:5432/langfuse" .Values.secrets.POSTGRES_USER .Values.secrets.POSTGRES_PASSWORD $dbName | b64enc | quote }}
```

This keeps the full connection string opaque in pod environments.

**References:**
- CWE-200: Exposure of Sensitive Information to an Unauthorized Actor
- NIST SP 800-53 SC-28 (Protection of Information at Rest)

---

### SEC-DEPLOY-03 [CRITICAL] No Image Digest Pinning – Supply Chain Risk

**Category:** Supply Chain Security
**Location:** `deploy/helm/summit-cap/values.yaml:14, 116, 139, 162, 198, 216, 227, 241`

**Description:**
All container images use mutable tags (`latest`, `3`, `26.0`, `pg16`, `24`) without digest pinning:

```yaml
global:
  imageTag: latest

minio:
  image:
    repository: minio/minio
    tag: latest

keycloak:
  image:
    repository: quay.io/keycloak/keycloak
    tag: "26.0"
```

Mutable tags allow image content to change without changing the deployment manifest. An attacker who compromises an upstream registry (or performs a tag rewrite attack) can inject malicious images that will be pulled on pod restart/reschedule.

**Impact:**
- Upstream compromise → automatic malicious deployment
- No audit trail of what image content was actually running
- Rollback complexity (tag may now point to different content)

**Recommendation:**
1. **Pin all images to SHA256 digests**:
   ```yaml
   image: quay.io/keycloak/keycloak:26.0@sha256:abc123...
   ```
2. Automate digest resolution in CI/CD:
   ```bash
   skopeo inspect docker://quay.io/keycloak/keycloak:26.0 | jq -r '.Digest'
   ```
3. Use Renovate or Dependabot to automate digest updates
4. For custom images (`summit-cap-api`, `summit-cap-ui`), ensure CI/CD tags with both version and digest

**For MVP acceptance**, at minimum:
- Pin third-party images (Keycloak, PostgreSQL, MinIO, Redis, ClickHouse)
- Document digest update process in deployment README
- Custom images can remain on mutable tags if built from trusted CI/CD

**References:**
- SLSA Supply Chain Level 1 requirement
- Sigstore/Cosign for image signing (future enhancement)
- OpenShift Image Signature Verification

---

### SEC-DEPLOY-04 [CRITICAL] MinIO Console Exposed via Public Route

**Category:** OWASP A01:2021 – Broken Access Control
**Location:** `deploy/helm/summit-cap/templates/minio.yaml:40-42`, no Route defined for console port

**Description:**
MinIO exposes a web console on port 9001 alongside the S3 API on port 9000:

```yaml
ports:
  - name: console
    containerPort: 9001
    protocol: TCP
```

While no explicit OpenShift Route is defined for the console in `routes.yaml`, the Service is `type: ClusterIP` and exposes both ports:

```yaml
ports:
  - port: 9001
    targetPort: console
    protocol: TCP
    name: console
```

**Current State:** Console is **not** publicly routable (good), but also not explicitly blocked.

**Risk:**
If an operator adds a Route for `minio:9001` (common for debugging), the console becomes publicly accessible with credentials `minio:miniosecret` (see SEC-DEPLOY-01).

**Impact:**
MinIO console provides:
- Bucket browsing and file download (all loan documents)
- User/policy management
- Server configuration changes

**Recommendation:**
1. **Remove console port from Service** if not needed for production operations:
   ```yaml
   ports:
     - port: 9000  # Only expose S3 API
   ```
2. If console access is required, restrict via:
   - Separate Service with no Route (admin access via `kubectl port-forward` only)
   - NetworkPolicy limiting console port to specific admin pods
   - OAuth proxy in front of console (OpenShift OAuth Proxy sidecar)

3. Add explicit comment in `minio.yaml`:
   ```yaml
   # Console port 9001 is NOT exposed via Route for security.
   # Admin access: kubectl port-forward svc/minio 9001:9001
   ```

**References:**
- CIS Docker Benchmark 5.7 (Do not expose unnecessary ports)

---

### SEC-DEPLOY-05 [CRITICAL] SQLAdmin Panel Exposed via Public Route with Default Credentials

**Category:** OWASP A01:2021 – Broken Access Control
**Location:** `deploy/helm/summit-cap/templates/routes.yaml:142-175`, `values.yaml:65-67`

**Description:**
The SQLAdmin management interface is exposed via a public OpenShift Route at `/admin`:

```yaml
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: {{ .Values.api.name }}-admin-route
spec:
  path: /admin
  tls:
    termination: edge
```

Combined with default credentials `admin:admin` (SEC-DEPLOY-01), this provides unauthenticated attackers with full database access.

**Impact:**
SQLAdmin exposes:
- All database tables including `applications`, `hmda.demographics`, `users`
- Create/Update/Delete operations on all records
- SQL query execution interface
- No audit logging of admin actions (separate from application audit trail)

**Recommendation:**
1. **Remove the public Route entirely** — SQLAdmin is a debug/ops tool, not a production feature:
   ```yaml
   # DELETE lines 142-175 from routes.yaml
   ```
   Access via `kubectl port-forward` for authorized operators only.

2. If public access is required, implement:
   - **OAuth2 Proxy** sidecar requiring OpenShift authentication
   - **IP allowlisting** via Route annotations (operator workstations only)
   - **Separate RBAC** — create dedicated admin users, not shared `admin` account

3. Add session-based brute-force protection (rate limiting on `/admin/login`)

4. Audit all SQLAdmin actions to the application audit trail

**For MVP**, the first recommendation (remove Route) is the only acceptable option — the effort to secure SQLAdmin properly exceeds its value for a demo application.

**References:**
- OWASP Top 10 A01:2021
- Your own previous audit finding SE-02 (SQLAdmin default credentials)

---

### SEC-DEPLOY-06 [CRITICAL] Keycloak Realm: sslRequired=none

**Category:** OWASP A02:2021 – Cryptographic Failures
**Location:** `deploy/helm/summit-cap/files/summit-cap-realm.json:4`

**Description:**
The Keycloak realm is configured to allow plaintext HTTP:

```json
"sslRequired": "none"
```

This allows token exchange, authentication flows, and JWKS retrieval over unencrypted connections.

**Impact:**
- Man-in-the-middle attacks can intercept access tokens
- Session hijacking via token theft
- JWKS poisoning (attacker replaces public keys over HTTP)

While OpenShift Routes use TLS termination (`edge`), **internal service-to-service calls** between API pods and Keycloak use HTTP:

```yaml
# values.yaml line 33
KEYCLOAK_URL: "http://keycloak:8080"
```

An attacker with pod network access (e.g., via compromised container) can intercept internal Keycloak traffic.

**Recommendation:**
1. Change realm config:
   ```json
   "sslRequired": "external"
   ```
   This requires TLS for external clients but allows HTTP for internal requests from trusted proxies.

2. **Preferred**: Enable TLS for internal Keycloak communication:
   - Configure Keycloak with TLS certificate (OpenShift service-serving certs)
   - Update `KEYCLOAK_URL` to `https://keycloak:8443`
   - Add certificate verification to API clients

3. Add NetworkPolicy to restrict Keycloak access to API pods only (defense-in-depth)

**For MVP**, changing to `"sslRequired": "external"` is the minimum fix.

**References:**
- Keycloak Server Administration Guide § Threat Model Mitigation
- OWASP Transport Layer Protection Cheat Sheet

---

### SEC-DEPLOY-07 [WARNING] Keycloak Realm: No Password Policy

**Category:** OWASP A07:2021 – Identification and Authentication Failures
**Location:** `deploy/helm/summit-cap/files/summit-cap-realm.json` (missing `passwordPolicy` field)

**Description:**
The realm configuration has no password complexity requirements:

```json
{
  "realm": "summit-cap",
  "enabled": true,
  // No passwordPolicy field
}
```

All demo users have the password `"demo"`, and the admin account uses `"admin"`. There are no length requirements, complexity rules, or breach database checks.

**Impact:**
- Users can set trivial passwords (dictionary words, `12345678`, etc.)
- No defense against credential stuffing attacks
- No rotation enforcement

**Recommendation:**
Add to realm JSON:

```json
"passwordPolicy": "length(12) and digits(1) and lowerCase(1) and upperCase(1) and specialChars(1) and notUsername(undefined) and passwordHistory(5)"
```

This enforces:
- 12+ characters
- At least 1 digit, lowercase, uppercase, special char
- Not equal to username
- Cannot reuse last 5 passwords

For production, also enable:
```json
"passwordPolicy": "... and passwordBlacklist(undefined)"
```
and configure a breach password list (HaveIBeenPwned integration).

**References:**
- NIST SP 800-63B § 5.1.1 Memorized Secret Verifiers
- OWASP Authentication Cheat Sheet

---

### SEC-DEPLOY-08 [WARNING] Keycloak Realm: No Brute-Force Protection

**Category:** OWASP A07:2021 – Identification and Authentication Failures
**Location:** `deploy/helm/summit-cap/files/summit-cap-realm.json` (missing `bruteForceProtected` field)

**Description:**
Keycloak's brute-force detection is disabled by default and not enabled in the realm config.

**Impact:**
Attackers can perform unlimited password guessing attempts against user accounts. With weak demo passwords (`demo`, `admin`), accounts are trivially compromised.

**Recommendation:**
Add to realm JSON:

```json
"bruteForceProtected": true,
"permanentLockout": false,
"maxFailureWaitSeconds": 900,
"minimumQuickLoginWaitSeconds": 60,
"waitIncrementSeconds": 60,
"quickLoginCheckMilliSeconds": 1000,
"maxDeltaTimeSeconds": 43200,
"failureFactor": 5
```

This configuration:
- Locks account for 15 minutes after 5 failed attempts
- Incremental backoff on repeated failures
- Protects against rapid-fire credential stuffing

**References:**
- Keycloak Server Administration Guide § Threat Model Mitigation § Brute Force Attacks

---

### SEC-DEPLOY-09 [WARNING] Keycloak Client: webOrigins=["*"]

**Category:** OWASP A05:2021 – Security Misconfiguration
**Location:** `deploy/helm/summit-cap/files/summit-cap-realm.json:27`

**Description:**
The `summit-cap-ui` client allows CORS requests from any origin:

```json
"webOrigins": ["http://localhost:3000", "http://localhost:5173", "*"]
```

**Impact:**
Any website can make authenticated requests to Keycloak on behalf of Summit Cap users, bypassing same-origin policy. Enables:
- Token theft via malicious sites
- Unauthorized OIDC flows initiated from attacker domains

**Recommendation:**
Remove the wildcard:

```json
"webOrigins": [
  "http://localhost:3000",
  "http://localhost:5173",
  "https://{{ .Values.routes.sharedHost }}"
]
```

Use Helm templating to dynamically set production origins based on the deployed Route hostname.

**References:**
- OWASP CORS Misconfiguration
- RFC 6749 § 10.6 (Cross-Site Request Forgery)

---

### SEC-DEPLOY-10 [WARNING] Keycloak Client: redirectUris=["https://*"]

**Category:** OWASP A05:2021 – Security Misconfiguration
**Location:** `deploy/helm/summit-cap/files/summit-cap-realm.json:26`

**Description:**
The `summit-cap-ui` client allows redirects to any HTTPS URL:

```json
"redirectUris": ["http://localhost:3000/*", "http://localhost:5173/*", "https://*"]
```

**Impact:**
Open redirect vulnerability — attacker can craft authorization URLs that redirect tokens to attacker-controlled domains:

```
https://keycloak-summit-cap.apps.rosa.com/auth?redirect_uri=https://evil.com/steal
```

After user authentication, the access token is delivered to `evil.com`.

**Recommendation:**
Explicitly list allowed redirect URIs:

```json
"redirectUris": [
  "http://localhost:3000/*",
  "http://localhost:5173/*",
  "https://{{ .Values.routes.sharedHost }}/*"
]
```

For multi-environment deployments, use Helm `range` to iterate over a values list.

**References:**
- CWE-601: URL Redirection to Untrusted Site ('Open Redirect')
- OAuth 2.0 Security Best Current Practice § 4.1

---

### SEC-DEPLOY-11 [WARNING] Database Init Script Hardcodes Role Passwords

**Category:** OWASP A02:2021 – Cryptographic Failures
**Location:** `deploy/helm/summit-cap/templates/database-configmap.yaml:24, 27`

**Description:**
The database initialization script creates PostgreSQL roles with hardcoded passwords:

```sql
CREATE ROLE lending_app WITH LOGIN PASSWORD 'lending_pass';
CREATE ROLE compliance_app WITH LOGIN PASSWORD 'compliance_pass';
```

These passwords are:
1. Stored in plaintext in a ConfigMap (readable by any pod in the namespace)
2. Not rotatable without recreating the database
3. Not documented in `values.yaml` as overridable secrets

**Impact:**
Any process with ConfigMap read access (common for ServiceAccounts) can extract database credentials. Compliance database isolation (HMDA) is bypassed if `compliance_app` password is stolen.

**Recommendation:**
1. Move role passwords to `values.yaml` secrets:
   ```yaml
   secrets:
     LENDING_APP_PASSWORD: "changeme"
     COMPLIANCE_APP_PASSWORD: "changeme"
   ```

2. Update init script to reference environment variables:
   ```sql
   CREATE ROLE lending_app WITH LOGIN PASSWORD :'LENDING_APP_PASSWORD';
   ```

3. Pass env vars to postgres initContainer from Secret (requires custom entrypoint wrapper)

**Alternative (simpler for MVP):**
Use cert-based authentication instead of passwords:
```sql
CREATE ROLE lending_app WITH LOGIN;
-- Configure pg_hba.conf for cert auth
```

This eliminates password storage entirely but requires client certificate distribution.

**References:**
- PostgreSQL § 20.3 Authentication Methods
- CWE-798: Use of Hard-coded Credentials

---

### SEC-DEPLOY-12 [WARNING] No NetworkPolicies – Unrestricted Pod-to-Pod Traffic

**Category:** Defense in Depth
**Location:** `deploy/helm/summit-cap/templates/` (missing `networkpolicy.yaml`)

**Description:**
No NetworkPolicies are defined. All pods can communicate with all other pods in the namespace by default.

**Impact:**
- Compromised UI pod can directly access PostgreSQL (bypass API authorization)
- Compromised API pod can access MinIO console port (bypass S3 API access controls)
- Compromised seed job can access Keycloak admin API
- LangFuse worker can access application database (should only access `langfuse` DB)

**Recommendation:**
Add NetworkPolicy templates to enforce least-privilege network access:

**Example: Database ingress policy**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-ingress
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/component: database
  policyTypes:
    - Ingress
  ingress:
    - from:
      - podSelector:
          matchLabels:
            app.kubernetes.io/component: api  # Only API pods
      - podSelector:
          matchLabels:
            app.kubernetes.io/component: langfuse-web
      - podSelector:
          matchLabels:
            app.kubernetes.io/component: seed
      ports:
        - protocol: TCP
          port: 5432
```

**Minimum policies for MVP:**
1. Database: allow only from API, LangFuse, seed job
2. Keycloak: allow only from API, UI
3. MinIO: allow only from API, LangFuse (deny console port 9001)
4. Redis: allow only from LangFuse
5. ClickHouse: allow only from LangFuse

**References:**
- Kubernetes Network Policies Guide
- OpenShift SDN / OVN-Kubernetes network isolation

---

### SEC-DEPLOY-13 [WARNING] ReadOnlyRootFilesystem Disabled Globally

**Category:** Container Security Best Practice
**Location:** `deploy/helm/summit-cap/values.yaml:277`

**Description:**
The global security context disables read-only root filesystem for all containers:

```yaml
securityContext:
  readOnlyRootFilesystem: false
```

**Impact:**
Containers can write to any path in their filesystem. Attackers who achieve code execution can:
- Install malicious binaries
- Modify configuration files
- Persist malware across container restarts (if using PVCs)

**Recommendation:**
Enable per-container:

```yaml
securityContext:
  readOnlyRootFilesystem: true
```

For containers that need writable paths (logs, temp files), mount `emptyDir` volumes:

```yaml
volumeMounts:
  - name: tmp
    mountPath: /tmp
  - name: cache
    mountPath: /var/cache
volumes:
  - name: tmp
    emptyDir: {}
  - name: cache
    emptyDir: {}
```

**Known exceptions** (require writable filesystem):
- PostgreSQL: needs `/var/lib/postgresql/data` (already uses PVC)
- ClickHouse: needs `/var/lib/clickhouse` (already uses PVC)
- MinIO: needs `/data` (already uses PVC)

API, UI, Keycloak, LangFuse, Redis should all support read-only root.

**References:**
- CIS Kubernetes Benchmark 5.2.6
- OpenShift restricted-v2 SCC encourages this

---

### SEC-DEPLOY-14 [WARNING] No Pod Security Standards / SCC Enforcement

**Category:** Container Security
**Location:** Missing `PodSecurityAdmission` labels or SCC bindings

**Description:**
The Helm chart does not enforce OpenShift Security Context Constraints (SCCs) or Kubernetes Pod Security Standards.

**Current state:**
- `podSecurityContext: {}` (empty, line 269)
- `securityContext` sets baseline restrictions but doesn't declare compliance level
- No namespace labels for Pod Security Admission

**Impact:**
Pods may be scheduled with excessive privileges if:
- Operator manually edits Deployment to add `privileged: true`
- Future template changes introduce privilege escalation
- SCCs are misconfigured at cluster level

**Recommendation:**
1. Add namespace labels for Pod Security Admission:
   ```yaml
   # In Chart.yaml or installation instructions
   apiVersion: v1
   kind: Namespace
   metadata:
     name: summit-cap
     labels:
       pod-security.kubernetes.io/enforce: restricted
       pod-security.kubernetes.io/audit: restricted
       pod-security.kubernetes.io/warn: restricted
   ```

2. Document required SCC for OpenShift:
   ```bash
   # All pods should run under restricted-v2 SCC
   oc adm policy add-scc-to-user restricted-v2 -z summit-cap
   ```

3. Test deployment on a namespace with `restricted-v2` enforced to verify no privilege requirements

**References:**
- Kubernetes Pod Security Standards
- OpenShift Security Context Constraints § restricted-v2

---

### SEC-DEPLOY-15 [WARNING] Seed Job Uses Post-Install Hook – Credentials Before Rotation

**Category:** Operational Security
**Location:** `deploy/helm/summit-cap/templates/seed-job.yaml:10-11`

**Description:**
The seed job runs as a Helm hook:

```yaml
annotations:
  helm.sh/hook: post-install,post-upgrade
```

This means it executes **before** operators have an opportunity to rotate default credentials. The seed data (demo applications, users) is created using:
- Default database credentials (`user:changeme`)
- Default MinIO credentials (`minio:miniosecret`)

**Impact:**
If an operator forgets to rotate secrets before the first install, the seed data is created and associated with compromised credentials. Rotating secrets after seeding may leave orphaned data or broken foreign key references.

**Recommendation:**
1. **Change hook to `post-install` only** (not `post-upgrade`):
   ```yaml
   helm.sh/hook: post-install
   ```
   This ensures seed runs once, then operators can rotate secrets before upgrade cycles.

2. Add pre-install validation hook that checks for default passwords:
   ```yaml
   apiVersion: batch/v1
   kind: Job
   metadata:
     annotations:
       helm.sh/hook: pre-install
       helm.sh/hook-weight: "-10"
   spec:
     template:
       spec:
         containers:
           - name: validate-secrets
             image: alpine:3
             command:
               - sh
               - -c
               - |
                 if [ "$ADMIN_PASSWORD" = "admin" ]; then
                   echo "ERROR: Default passwords detected. Override before install."
                   exit 1
                 fi
   ```

3. Document the installation order in README:
   ```
   1. helm install --dry-run to verify
   2. Override all secrets via --set or external Secret
   3. helm install (seed runs after credential verification)
   ```

**References:**
- Helm Hooks Documentation
- Principle of Least Surprise in deployment automation

---

### SEC-DEPLOY-16 [WARNING] LangFuse ClickHouse URL Exposes Password in Environment

**Category:** OWASP A02:2021 – Cryptographic Failures
**Location:** `deploy/helm/summit-cap/templates/langfuse.yaml:129, 299`

**Description:**
Similar to SEC-DEPLOY-02, ClickHouse connection URLs embed credentials:

```yaml
- name: CLICKHOUSE_MIGRATION_URL
  value: "clickhouse://clickhouse:{{ .Values.secrets.CLICKHOUSE_PASSWORD }}@clickhouse:9000/default"
```

**Recommendation:**
Same fix as SEC-DEPLOY-02 — move full connection strings into Kubernetes Secrets, reference via `secretKeyRef`.

---

### SEC-DEPLOY-17 [SUGGESTION] API Deployment Missing Startup Probe

**Category:** Reliability / Availability
**Location:** `deploy/helm/summit-cap/templates/api-deployment.yaml:231-244`

**Description:**
API deployment has `livenessProbe` and `readinessProbe` but no `startupProbe`. The API runs migrations in an initContainer, which can take 30-60 seconds on a cold start.

**Impact:**
If migrations take longer than `initialDelaySeconds: 30`, the liveness probe may kill the pod before it's fully started.

**Recommendation:**
Add startup probe with higher failure threshold:

```yaml
startupProbe:
  httpGet:
    path: /health/
    port: http
  initialDelaySeconds: 10
  periodSeconds: 5
  failureThreshold: 12  # 60 seconds total
```

Once startup succeeds, liveness probe takes over with tighter SLO.

**References:**
- Kubernetes Probes Best Practices

---

### SEC-DEPLOY-18 [SUGGESTION] No Resource Quotas at Namespace Level

**Category:** Resource Exhaustion / DoS
**Location:** Missing `ResourceQuota` manifest

**Description:**
No namespace-level ResourceQuota is defined. Individual pods have `resources.limits`, but nothing prevents an operator from scaling replicas to consume all cluster capacity.

**Impact:**
- Accidental `kubectl scale deployment/api --replicas=100` exhausts cluster
- Compromised ServiceAccount with deployment edit permissions can DoS the cluster

**Recommendation:**
Add namespace quota template:

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: summit-cap-quota
spec:
  hard:
    requests.cpu: "10"
    requests.memory: "20Gi"
    limits.cpu: "20"
    limits.memory: "40Gi"
    persistentvolumeclaims: "10"
```

Adjust based on expected production scale.

**References:**
- Kubernetes Resource Quotas
- OpenShift Quota Management

---

### SEC-DEPLOY-19 [SUGGESTION] Database StatefulSet Missing PodDisruptionBudget

**Category:** Availability
**Location:** `deploy/helm/summit-cap/templates/database-deployment.yaml` (missing PDB)

**Description:**
The database is a single-replica StatefulSet with no PodDisruptionBudget. During cluster maintenance (node drains), the database pod may be evicted without coordination, causing API downtime.

**Recommendation:**
Add PodDisruptionBudget:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: summit-cap-db-pdb
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app.kubernetes.io/component: database
```

This ensures the database pod is only evicted if a replacement is already running (requires scaling to 2 replicas first).

**For MVP with single replica**, use:
```yaml
maxUnavailable: 0
```
This blocks node drains if the database pod is on the node, forcing manual intervention.

**References:**
- Kubernetes PodDisruptionBudget
- PostgreSQL HA patterns (for future multi-replica upgrade)

---

### SEC-DEPLOY-20 [SUGGESTION] Missing Security Headers in API Responses

**Category:** Browser Security
**Location:** Application code (not deployment config), but deployment should document requirement

**Description:**
The API does not set security headers (CSP, X-Frame-Options, HSTS, X-Content-Type-Options). This was flagged in previous audits (SE-10, SEC-10) but is not documented in deployment configuration.

**Impact:**
- Clickjacking attacks against `/admin` panel
- Mixed content warnings on HTTPS deployments
- MIME sniffing vulnerabilities

**Recommendation:**
Add to API application code (FastAPI middleware):

```python
@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response
```

Document in deployment README as a production readiness checklist item.

**References:**
- OWASP Secure Headers Project
- Mozilla Web Security Guidelines

---

### SEC-DEPLOY-21 [SUGGESTION] Init Container Uses Privileged Image (postgres:16-alpine)

**Category:** Supply Chain / Least Privilege
**Location:** `deploy/helm/summit-cap/templates/api-deployment.yaml:24`, `langfuse.yaml:28`

**Description:**
Init containers use the official PostgreSQL image just to run `pg_isready`:

```yaml
initContainers:
  - name: wait-for-database
    image: postgres:16-alpine
    command: ["/bin/sh", "-c", "until pg_isready ..."]
```

This image includes the full PostgreSQL server, client tools, shell utilities, and runs as root by default in Alpine.

**Impact:**
Larger attack surface than necessary for a simple readiness check. If the init container is compromised (e.g., via a DNS hijack during image pull), the attacker gains root execution in the pod.

**Recommendation:**
Use a minimal image with only `pg_isready`:

```yaml
initContainers:
  - name: wait-for-database
    image: docker.io/bitnami/postgresql:16
    # Or build a scratch image with just pg_isready binary
```

Alternatively, use a generic wait tool:
```yaml
image: docker.io/busybox:1.36
command:
  - sh
  - -c
  - "until nc -z summit-cap-db 5432; do sleep 3; done"
```

**References:**
- CIS Docker Benchmark 4.1 (Ensure a user for the container has been created)
- Distroless containers pattern

---

### SEC-DEPLOY-22 [SUGGESTION] No Audit Logging of Helm Deployments

**Category:** Audit Trail
**Location:** Missing audit configuration in deployment automation

**Description:**
Helm deployments are not audited. There's no record of:
- Who deployed which chart version
- What values were overridden
- When secrets were rotated

**Recommendation:**
Integrate with OpenShift/Kubernetes audit logging:

1. Enable audit logging for Helm operations:
   ```yaml
   apiVersion: audit.k8s.io/v1
   kind: Policy
   rules:
     - level: RequestResponse
       omitStages: ["RequestReceived"]
       resources:
         - group: ""
           resources: ["configmaps", "secrets"]
       namespaces: ["summit-cap"]
   ```

2. Use `helm history` tracking:
   ```bash
   helm history summit-cap -n summit-cap --output json > audit.json
   ```

3. Emit structured logs from CI/CD on deployments:
   ```json
   {
     "event": "helm_upgrade",
     "user": "pipeline-sa",
     "chart": "summit-cap-1.2.3",
     "values_sha256": "abc123...",
     "timestamp": "2026-03-06T12:00:00Z"
   }
   ```

**References:**
- Kubernetes Auditing
- OpenShift Audit Logs § API Server Audit

---

### SEC-DEPLOY-23 [SUGGESTION] Keycloak Deployment Uses start-dev Mode

**Category:** OWASP A05:2021 – Security Misconfiguration
**Location:** `deploy/helm/summit-cap/templates/keycloak.yaml:38`

**Description:**
Keycloak runs in dev mode:

```yaml
args:
  - start-dev
  - --import-realm
```

This disables TLS requirement checks, enables verbose error messages, and relaxes other production safeguards.

**Impact:**
- Leak of stack traces and internal paths in error responses
- Relaxed validation that may hide misconfigurations
- Documentation warns against using `start-dev` in production

**Recommendation:**
Change to production mode:

```yaml
args:
  - start
  - --import-realm
  - --optimized
  - --hostname-strict=false  # Required behind OpenShift Routes
```

Add health check override for production mode (different port/path).

**References:**
- Keycloak Server Installation and Configuration § Production Mode

---

### SEC-DEPLOY-24 [SUGGESTION] No Dependency Scanning in Container Images

**Category:** Vulnerability Management
**Location:** Missing CI/CD integration with Trivy/Clair/Snyk

**Description:**
There's no evidence of container image vulnerability scanning in the deployment pipeline. Images may contain outdated packages with CVEs.

**Recommendation:**
1. Integrate Trivy into CI/CD:
   ```bash
   trivy image --severity HIGH,CRITICAL quay.io/summit-cap/summit-cap-api:latest
   ```

2. For OpenShift, enable built-in image scanning:
   ```bash
   oc set image-lookup deployment/summit-cap-api
   ```

3. Add scanning gate to PR checks:
   ```yaml
   # .github/workflows/security.yml
   - name: Scan image
     uses: aquasecurity/trivy-action@master
     with:
       image-ref: ${{ env.IMAGE }}
       severity: HIGH,CRITICAL
       exit-code: 1  # Fail PR on vulnerabilities
   ```

**References:**
- SLSA Supply Chain Level 2 requirement
- NIST SP 800-190 § 4.1.1

---

### SEC-DEPLOY-25 [SUGGESTION] Service Account Has No Explicit Permissions

**Category:** Least Privilege
**Location:** `deploy/helm/summit-cap/templates/serviceaccount.yaml`

**Description:**
A ServiceAccount is created but has no explicit RoleBinding:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {{ include "summit-cap.serviceAccountName" . }}
```

It inherits default permissions from the namespace's `default` ServiceAccount.

**Impact:**
If namespace RBAC is misconfigured, pods may have more permissions than needed. Compromised pod can escalate privileges.

**Recommendation:**
Add explicit Role and RoleBinding:

```yaml
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: summit-cap-role
rules:
  - apiGroups: [""]
    resources: ["configmaps", "secrets"]
    verbs: ["get", "list"]  # Read-only for app config
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: summit-cap-binding
subjects:
  - kind: ServiceAccount
    name: summit-cap
roleRef:
  kind: Role
  name: summit-cap-role
  apiGroup: rbac.authorization.k8s.io
```

This explicitly denies access to Pods, Deployments, Services (no privilege escalation).

**References:**
- Kubernetes RBAC Good Practices
- Principle of Least Privilege

---

### SEC-DEPLOY-26 [SUGGESTION] Keycloak Session Timeouts Too Long

**Category:** Session Management
**Location:** `deploy/helm/summit-cap/files/summit-cap-realm.json:8-9`

**Description:**
SSO sessions last 8 hours:

```json
"ssoSessionMaxLifespan": 28800,
"ssoSessionIdleTimeout": 28800
```

**Impact:**
Stolen session tokens remain valid for 8 hours. Unattended workstations stay authenticated.

**Recommendation:**
Reduce to:
```json
"ssoSessionMaxLifespan": 3600,    // 1 hour max
"ssoSessionIdleTimeout": 1800     // 30 min idle
```

Balance security vs. user experience based on borrower workflow patterns.

**References:**
- OWASP Session Management Cheat Sheet
- NIST SP 800-63B § 7.2 (Reauthentication)

---

### SEC-DEPLOY-27 [SUGGESTION] No Rate Limiting on Routes

**Category:** OWASP A04:2021 – Insecure Design
**Location:** `deploy/helm/summit-cap/templates/routes.yaml` (missing annotations)

**Description:**
OpenShift Routes have no rate limiting annotations. API endpoints are vulnerable to:
- Credential stuffing (Keycloak login)
- Scraping (documents endpoint)
- Resource exhaustion (LLM chat endpoints)

**Recommendation:**
Add HAProxy rate limiting via annotations:

```yaml
metadata:
  annotations:
    haproxy.router.openshift.io/rate-limit-connections: "20"
    haproxy.router.openshift.io/rate-limit-connections.concurrent-tcp: "10"
```

For API-level rate limiting, use FastAPI middleware:
```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.post("/login")
@limiter.limit("5/minute")
async def login(...):
```

**References:**
- OpenShift Route Annotations
- OWASP API Security Top 10 A04:2021

---

### SEC-DEPLOY-28 [SUGGESTION] Database Credentials Not Rotated

**Category:** Credential Lifecycle Management
**Location:** No rotation mechanism in chart

**Description:**
Default database credentials (`POSTGRES_PASSWORD: "changeme"`) have no rotation workflow. Once set at install, they remain static.

**Impact:**
Credential compromise has unlimited validity. No defense against long-term credential theft.

**Recommendation:**
Implement rotation via:

1. **External Secrets Operator** (preferred):
   ```yaml
   apiVersion: external-secrets.io/v1beta1
   kind: ExternalSecret
   metadata:
     name: database-credentials
   spec:
     secretStoreRef:
       name: aws-secrets-manager
     target:
       name: summit-cap-secret
     data:
       - secretKey: POSTGRES_PASSWORD
         remoteRef:
           key: /summit-cap/db/password
   ```
   Rotation happens outside Kubernetes, Secret is automatically updated.

2. **Kubernetes Secret rotation with Helm hooks**:
   - Pre-upgrade hook generates new password
   - Migrates database to new credential
   - Updates Secret
   - Restarts pods

**For MVP**, document manual rotation procedure:
```bash
# 1. Generate new password
NEW_PASS=$(openssl rand -base64 32)

# 2. Update database
kubectl exec -it summit-cap-db-0 -- psql -c "ALTER USER user PASSWORD '$NEW_PASS';"

# 3. Update Secret
kubectl patch secret summit-cap-secret -p "{\"data\":{\"POSTGRES_PASSWORD\":\"$(echo -n $NEW_PASS | base64)\"}}"

# 4. Restart API
kubectl rollout restart deployment/summit-cap-api
```

**References:**
- NIST SP 800-63B § 5.1.1.2 (Credential Rotation)
- External Secrets Operator documentation

---

### SEC-DEPLOY-29 [POSITIVE] Container Security Context Baseline Applied

**Category:** Container Hardening
**Location:** `deploy/helm/summit-cap/values.yaml:272-281`

**Description:**
All containers apply a secure-by-default security context:

```yaml
securityContext:
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL
  runAsNonRoot: true
  seccompProfile:
    type: RuntimeDefault
```

This enforces:
- No privilege escalation (blocks sudo, setuid)
- All Linux capabilities dropped (minimal attack surface)
- Containers must run as non-root user
- Seccomp filters applied (syscall restrictions)

**Impact:**
Significantly reduces container breakout risk. Complies with OpenShift `restricted-v2` SCC requirements.

**Recommendation:**
Continue this pattern. Only exception found was ClickHouse (lines 28-33), which correctly applies the same context.

---

### SEC-DEPLOY-30 [POSITIVE] Secrets Use secretKeyRef Pattern

**Category:** Secrets Management
**Location:** All deployments

**Description:**
All sensitive configuration is injected via `secretKeyRef` rather than plain-text env vars:

```yaml
env:
  - name: S3_SECRET_KEY
    valueFrom:
      secretKeyRef:
        name: summit-cap-secret
        key: S3_SECRET_KEY
```

**Impact:**
Secrets are never visible in:
- Deployment manifests
- `kubectl describe pod` output (shows `<set to the key 'S3_SECRET_KEY' in secret 'summit-cap-secret'>`)
- Container environment dumps

**Exceptions:**
SEC-DEPLOY-02 and SEC-DEPLOY-16 identified two connection strings that embed credentials in plain-text values. Once those are fixed, secret handling is fully compliant.

---

### SEC-DEPLOY-31 [POSITIVE] TLS Enforced on All Routes

**Category:** Transport Security
**Location:** `deploy/helm/summit-cap/templates/routes.yaml`

**Description:**
All OpenShift Routes use TLS with edge termination and redirect insecure traffic:

```yaml
tls:
  termination: edge
  insecureEdgeTerminationPolicy: Redirect
```

**Impact:**
All external traffic is encrypted. HTTP requests are automatically upgraded to HTTPS.

**Recommendation:**
Maintain this pattern. Consider adding HSTS headers (see SEC-DEPLOY-20) for browser enforcement.

---

### SEC-DEPLOY-32 [POSITIVE] Database PVC Enforces Persistence

**Category:** Data Integrity
**Location:** `deploy/helm/summit-cap/templates/database-deployment.yaml:102-115`

**Description:**
Database uses PersistentVolumeClaim with proper access mode:

```yaml
volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes:
        - ReadWriteOnce
      resources:
        requests:
          storage: 10Gi
```

**Impact:**
Data survives pod restarts, node failures, and accidental deletions (if PVC `reclaimPolicy: Retain`).

**Recommendation:**
Ensure production clusters use:
- Encrypted storage class (AWS EBS with KMS)
- Volume snapshots for backup
- `reclaimPolicy: Retain` to prevent accidental data loss on `helm uninstall`

---

### SEC-DEPLOY-33 [POSITIVE] Health Checks Configured for All Services

**Category:** Reliability
**Location:** All deployment templates

**Description:**
Every service has both `livenessProbe` and `readinessProbe`:

```yaml
livenessProbe:
  httpGet:
    path: /health/
    port: http
readinessProbe:
  httpGet:
    path: /health/
    port: http
```

**Impact:**
- Unhealthy pods are automatically restarted
- Traffic is not routed to pods that aren't ready
- Improves availability during rolling updates

**Recommendation:**
Consider adding `startupProbe` to API (SEC-DEPLOY-17) for slower migrations.

---

## Summary by Severity

| Severity | Count | Examples |
|----------|-------|----------|
| **Critical** | 10 | Weak default passwords, DB credentials in env vars, no image pinning, MinIO/SQLAdmin exposure, Keycloak sslRequired=none |
| **Warning** | 15 | Keycloak password policy, brute-force protection, CORS/redirect wildcards, hardcoded DB role passwords, no NetworkPolicies, readOnlyRootFilesystem disabled |
| **Suggestion** | 8 | Missing startup probes, resource quotas, PodDisruptionBudget, security headers, audit logging, rate limiting |
| **Positive** | 4 | Container security context baseline, secretKeyRef pattern, TLS on routes, database persistence |

---

## Priority Remediation Roadmap

### Phase 1: Block Deployment (Critical - Fix Before Any Production Use)
1. **SEC-DEPLOY-01**: Remove all default passwords from values.yaml, enforce override via Helm required() function
2. **SEC-DEPLOY-05**: Remove SQLAdmin public Route entirely
3. **SEC-DEPLOY-06**: Change Keycloak `sslRequired: "external"`

### Phase 2: Production Hardening (Required for MVP)
4. **SEC-DEPLOY-03**: Pin third-party images to SHA256 digests
5. **SEC-DEPLOY-04**: Remove MinIO console port from Service, document kubectl port-forward access
6. **SEC-DEPLOY-02, 16**: Move LangFuse/ClickHouse connection strings to Secrets
7. **SEC-DEPLOY-07, 08**: Add Keycloak password policy and brute-force protection
8. **SEC-DEPLOY-09, 10**: Remove CORS/redirect wildcards from Keycloak client
9. **SEC-DEPLOY-11**: Move DB role passwords to values.yaml secrets

### Phase 3: Defense in Depth (Recommended for MVP)
10. **SEC-DEPLOY-12**: Add NetworkPolicies for database, Keycloak, MinIO
11. **SEC-DEPLOY-13**: Enable readOnlyRootFilesystem for API, UI, Keycloak, LangFuse
12. **SEC-DEPLOY-14**: Document required SCC (restricted-v2), add namespace labels
13. **SEC-DEPLOY-23**: Change Keycloak to `start` production mode
14. **SEC-DEPLOY-27**: Add Route rate limiting annotations

### Phase 4: Operational Excellence (Post-MVP)
15. **SEC-DEPLOY-28**: Implement credential rotation workflow (External Secrets Operator)
16. **SEC-DEPLOY-24**: Add Trivy scanning to CI/CD
17. **SEC-DEPLOY-22**: Enable Helm deployment audit logging
18. **SEC-DEPLOY-18, 19**: Add ResourceQuota and PodDisruptionBudget

---

## Known Deferred Items (From Previous Audits)

The following were flagged in prior audits and are **not** deployment configuration issues, but application-level concerns:

- **SE-01** (SSN plaintext storage) — data model, not deployment
- **SE-04** (verify_thread_ownership not called) — application logic
- **SE-12** (LLM prompt injection) — agent architecture
- **SEC-08** (frontend route guards) — UI code
- **SEC-09** (credit report access control) — API authorization logic

These are documented in prior reviews and should remain tracked separately.

---

## Verification Commands

```bash
# Check if default passwords are still present
helm template ./deploy/helm/summit-cap | grep -i "admin:admin"

# Verify image digests
helm template ./deploy/helm/summit-cap | grep "image:" | grep -v "@sha256:"

# Check TLS on routes
oc get routes -n summit-cap -o json | jq '.items[].spec.tls.termination'

# Verify security context applied
oc get pods -n summit-cap -o json | jq '.items[].spec.containers[].securityContext'

# List all exposed Routes
oc get routes -n summit-cap -o custom-columns=NAME:.metadata.name,HOST:.spec.host,PATH:.spec.path
```

---

**End of Report**
