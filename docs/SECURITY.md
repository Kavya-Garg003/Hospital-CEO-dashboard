# 🔒 Security Documentation — Aarogya Hospital CEO Dashboard

## Threat Model

| Threat | Mitigation |
|--------|-----------|
| Unauthorized PHI access | AES-256-GCM field encryption + RBAC |
| JWT token theft | RS256 asymmetric signing + 15-min expiry |
| SQL injection | SQLAlchemy ORM parameterized queries only |
| XSS | React JSX auto-escaping + CSP headers |
| CSRF | SameSite=Strict cookie + CSRF token |
| Brute force login | slowapi rate limiting (100/min) + bcrypt |
| Man-in-the-middle | TLS enforced + HSTS header |
| Data leakage in AI | No PHI in Claude API prompts (aggregated stats only) |
| Audit tampering | SHA-256 hash of every audit entry |
| Key compromise | Keys in .env, never in source code |

## Encryption Architecture

### Field-Level Encryption (AES-256-GCM)

```
Plaintext PHI → AES-256-GCM Encrypt → base64(nonce || ciphertext || auth_tag) → Database
```

**Encrypted fields:**
- `patients.name_encrypted` — Full name
- `patients.phone_encrypted` — Phone number
- `patients.aadhaar_encrypted` — Aadhaar number
- `patients.diagnosis_encrypted` — Diagnosis text
- `appointments.patient_name_encrypted` — Appointment patient name

**Why AES-GCM?**
- Authenticated encryption (prevents tampering — auth tag verification)
- 256-bit key = post-quantum resistant for near future
- Random 12-byte nonce per encryption call = no IV reuse
- Industry standard for medical data (HIPAA, HL7 FHIR)

### Key Management

```
ENCRYPTION_KEY (64 hex = 32 bytes = 256-bit) stored in .env
↓
Never in source code, never committed to git
↓
For key rotation: decrypt all rows with old key, re-encrypt with new key
```

### Aadhaar Handling (RBI / UIDAI Guidelines)

```
Raw Aadhaar → SHA-256(aadhaar) → stored as aadhaar_hash (for dedup)
Raw Aadhaar → AES-256-GCM     → stored as aadhaar_encrypted
```

## Authentication

### JWT RS256 Flow

```
Login → bcrypt verify → create_access_token (RS256, 15min) 
                      → create_refresh_token (RS256, 7day, httpOnly cookie)
↓
Request → Bearer token → decode with PUBLIC key → RBAC check
```

**Why RS256?**
- Asymmetric: private key signs, public key verifies
- Microservice-ready: services can verify without sharing secret
- More secure than HS256 for distributed systems

### RBAC Matrix

| Permission | CEO | Dept Head | Finance |
|-----------|-----|-----------|---------|
| All endpoints | ✅ | ❌ | ❌ |
| Own dept patients | ✅ | ✅ | ❌ |
| Finance data | ✅ | ❌ | ✅ |
| Insurance data | ✅ | ❌ | ✅ |
| AI Concierge | ✅ | ✅ | ✅ |
| NABH/DPDP admin | ✅ | ❌ | ❌ |
| Audit log view | ✅ | ❌ | ❌ |
| Export PDF/Excel | ✅ | ❌ | ✅ |

## Security Headers (applied by middleware)

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Strict-Transport-Security: max-age=31536000; includeSubDomains  (production only)
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; ...
```

## Rate Limiting

- Default: 100 requests/minute per IP (slowapi)
- AI Chat: 10 requests/minute per IP
- Returns HTTP 429 with Retry-After header on breach

## Audit Log

Every data access creates an immutable entry:
```sql
INSERT INTO audit_log (timestamp, user_id, user_role, action, resource_type, 
                        resource_id, ip_address, session_id, data_hash)
VALUES (NOW(), ?, ?, ?, ?, ?, ?, ?, SHA256(?));
```

**Retained for 7 years** (NABH requirement).  
**No UPDATE or DELETE** operations on this table.

## Incident Response

1. Detect breach: audit log shows unusual patterns
2. Immediately revoke all JTIs (mass logout via token_blacklist)
3. Rotate ENCRYPTION_KEY (emergency key rotation procedure)
4. Notify DPO within 72 hours (DPDP Act 2023, S.8 obligation)
5. Document in incident register

## Key Rotation Procedure

```python
# Emergency key rotation (run as maintenance script)
from encryption import FieldEncryptor

old_encryptor = FieldEncryptor(OLD_KEY_HEX)
new_encryptor = FieldEncryptor(NEW_KEY_HEX)

# For each patient record:
plaintext = old_encryptor.decrypt(row.name_encrypted)
row.name_encrypted = new_encryptor.encrypt(plaintext)
# Repeat for all encrypted fields
```
