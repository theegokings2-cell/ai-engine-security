# Security Checklist for AI Office Manager

**Last Updated:** 2026-02-03
**Classification:** Internal - Development

---

## ✅ Critical Security Requirements (Must Complete Before PII)

### 1. Password Hashing ✅ FIXED 2026-02-03
- [x] Use bcrypt (not SHA256) for password hashing
- [x] Salt automatically handled by bcrypt
- [x] bcrypt work factor: 12 (default)

**Status:** ✅ COMPLETE

### 2. Secrets Management
- [ ] Change default JWT_SECRET_KEY in production
- [ ] Change default SECRET_KEY in production
- [ ] Use environment variables for all secrets
- [ ] Never commit secrets to git

**Commands to generate secure secrets:**
```bash
# Generate JWT secret (min 32 chars)
python -c "import secrets; print(secrets.token_hex(32))"

# Generate SECRET_KEY (min 64 chars)
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

**Status:** ⚠️ NEEDS ACTION - Update production .env

### 3. Database Security
- [ ] Enable SSL/TLS for PostgreSQL in production
- [ ] Use connection pooling with timeouts
- [ ] Enable audit logging for all data changes
- [ ] Regular database backups with encryption

**Status:** ⏳ PENDING

---

## 🔒 Production Security Requirements

### 4. HTTPS/TLS
- [ ] SSL certificate from Let's Encrypt or purchased CA
- [ ] Force redirect HTTP → HTTPS
- [ ] HSTS header enabled
- [ ] Certificate renewal automation

**Status:** ⏳ PENDING

### 5. CORS Configuration
- [ ] Whitelist only production domains
- [ ] No wildcard (`*`) origins
- [ ] Specific methods/headers allowed only

**Status:** ⚠️ DEV MODE - Needs production review

### 6. Rate Limiting
- [ ] Authentication endpoints: 5 attempts/minute
- [ ] API endpoints: 100 requests/minute
- [ ] File upload endpoints: 10 uploads/minute
- [ ] IP-based blocking for abuse

**Status:** ✅ IMPLEMENTED (see app/core/rate_limit.py)

### 7. Audit Logging
- [ ] Log all authentication attempts (success/fail)
- [ ] Log all data access (who accessed what)
- [ ] Log all data modifications (before/after)
- [ ] Log admin actions
- [ ] Log PII access
- [ ] Retain logs for minimum 90 days

**Status:** ⚠️ PARTIAL - Exception logging exists, need audit decorators

### 8. Input Validation
- [ ] Validate all user inputs
- [ ] Sanitize file uploads
- [ ] Limit request body sizes
- [ ] Prevent SQL injection (using SQLAlchemy)
- [ ] Prevent XSS (escaping output)
- [ ] Prevent CSRF tokens

**Status:** ✅ PARTIAL - SQL injection prevented, need CSRF

### 9. Dependency Security
- [ ] Regular vulnerability scans (Snyk/Dependabot)
- [ ] Automated PR security checks
- [ ] No high/critical CVEs in dependencies
- [ ] Pin dependency versions

**Status:** ⏳ PENDING

---

## 👤 Personal Data Protection (GDPR/Privacy Compliance)

### 10. Data Minimization
- [ ] Collect only necessary personal data
- [ ] Document what PII is collected and why
- [ ] Provide privacy policy
- [ ] Allow data export (GDPR right to portability)
- [ ] Allow data deletion (GDPR right to erasure)

**Status:** ⏳ PENDING

### 11. Data Access Controls
- [ ] Role-based access control (RBAC) ✅ Implemented
- [ ] Tenant isolation ✅ Implemented
- [ ] Employee vs Customer separation ✅ Designed
- [ ] Minimum privilege principle
- [ ] Regular access reviews

**Status:** ✅ IMPLEMENTED

### 12. Data Encryption
- [ ] Passwords hashed with bcrypt ✅
- [ ] Database at-rest encryption
- [ ] Backups encrypted
- [ ] Sensitive fields encrypted in DB (optional)

**Status:** ⚠️ PARTIAL - Passwords done, need rest

---

## 🚨 Incident Response

### 13. Security Incident Plan
- [ ] Document incident response procedures
- [ ] Define severity levels
- [ ] Assign incident response team
- [ ] Create communication templates
- [ ] Define escalation procedures
- [ ] Test incident response plan

**Status:** ⏳ PENDING

### 14. Breach Notification
- [ ] Define what constitutes a breach
- [ ] Create breach notification templates
- [ ] Define notification timeline (GDPR: 72 hours)
- [ ] Document authorities to notify

**Status:** ⏳ PENDING

---

## 📋 Quick Security Audit Commands

```bash
# Check for secrets in git history
git log --all -p | grep -E "SECRET_KEY|JWT|PASSWORD|API_KEY" | head -20

# Check installed dependencies for CVEs
pip audit

# Check for default passwords
grep -r "password123\|admin123\|change-me" .

# Check file permissions
ls -la .env
```

---

## 🎯 Priority Actions for This Week

1. **CRITICAL:** Update production JWT_SECRET_KEY
2. **CRITICAL:** Update production SECRET_KEY
3. **HIGH:** Enable HTTPS in production
4. **HIGH:** Add CSRF protection
5. **MEDIUM:** Add comprehensive audit logging
6. **MEDIUM:** Set up dependency scanning

---

## 📚 Compliance References

- **OWASP Top 10:** https://owasp.org/www-project-top-ten/
- **OWASP ASVS:** https://owasp.org/www-project-application-security-verification-standard/
- **GDPR:** https://gdpr.eu/
- **NIST Cybersecurity:** https://www.nist.gov/cyberframework

---

**Questions?** Contact the security team or review OWASP guidelines.
