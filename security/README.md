# Enterprise Security Framework

**Security-First Development for Multibillion-Dollar Applications**

---

## Overview

This security framework provides comprehensive protection for all applications developed in this workspace. It implements:

- **OWASP ASVS Level 2** compliance requirements
- **OWASP Top 10 2021** vulnerability prevention
- **AI/LLM Security** (OWASP Top 10 for LLMs)
- **Secure Supply Chain** practices
- **Vulnerability Management** with HackerOne integration

## Quick Start

```bash
# Clone the security framework
cd security

# Install lab dependencies
pip install -r labs/lab-requirements.txt

# Run security scan
cd github-actions
# See CI/CD integration below
```

## Directory Structure

```
security/
├── requirements/
│   └── OWASP-ASVS-Compliance.md   # Full security requirements
├── github-actions/
│   ├── security-scan-suite.yml    # CI/CD security scanning
│   └── dependabot.yml             # Dependency management
├── labs/
│   ├── prompt-injection-lab.md    # LLM security exercises
│   └── lab-requirements.txt       # Lab dependencies
├── knowledge/
│   └── vulnerability-kb.md        # Common vulnerabilities & fixes
└── skill-security/
    └── SKILL.md                   # Clawdbot security skill
```

## Security Requirements (P0 Priority)

All applications MUST comply with:

| Category | Priority | Status |
|----------|----------|--------|
| Tenant Isolation | P0 | Mandatory |
| Input Sanitization | P0 | Mandatory |
| Authentication/Authorization | P0 | Mandatory |
| Dependency Scanning | P0 | Mandatory |
| Secret Detection | P0 | Mandatory |
| RBAC Implementation | P0 | Mandatory |

See [OWASP-ASVS-Compliance.md](requirements/OWASP-ASVS-Compliance.md) for full requirements.

## CI/CD Integration

### GitHub Actions Security Suite

```yaml
# In your .github/workflows/ci.yml
jobs:
  security-scan:
    uses: ./.github/workflows/security-scan-suite.yml
```

The security scan includes:
- SAST (Bandit, Semgrep)
- Dependency Scanning (pip-audit, Safety)
- Secret Scanning (TruffleHog)
- Container Scanning (Trivy)
- DAST (ZAP)

### Dependabot Configuration

Enable in GitHub:
1. Settings → Security → Dependabot
2. Enable "Dependabot security updates"
3. Enable "Dependency graph"

Configuration: [dependabot.yml](github-actions/dependabot.yml)

## Vulnerability Management

### Severity Ratings

| Rating | CVSS | Response Time |
|--------|------|---------------|
| Critical | 9.0-10.0 | 24 hours |
| High | 7.0-8.9 | 7 days |
| Medium | 4.0-6.9 | 30 days |
| Low | 0.1-3.9 | 90 days |

### HackerOne Integration

- **Bug Bounty Program:** Active
- **Scope:** `*.ourapp.com`
- **Bounty Range:** $500 - $50,000

## AI/LLM Security

Special considerations for AI-powered applications:

### Prompt Injection Defense

See [labs/prompt-injection-lab.md](labs/prompt-injection-lab.md) for hands-on exercises.

### Key Mitigations

1. **Input Sanitization:** Filter injection patterns
2. **Context Isolation:** Separate system/user prompts
3. **Output Filtering:** Remove sensitive data
4. **Rate Limiting:** Prevent DoS via tokens

## Security Skill

The Clawdbot security skill provides guidance:

```markdown
When you need security advice, just ask! The skill provides:
- OWASP compliance guidance
- Vulnerability assessments
- Secure coding patterns
- RBAC implementation help
```

## Testing

### Automated Tests

Run security tests locally:

```bash
# SAST
bandit -r . -f json -o bandit-results.json

# Dependencies
safety check -r requirements.txt

# Secrets
trufflehog filesystem .
```

### Manual Testing

| Test Type | Frequency | Team |
|-----------|-----------|------|
| Penetration Testing | Quarterly | External |
| Red Team | Bi-annually | External |
| Code Review | Every PR | Peer |

## Documentation

### Required Documentation

- [x] Security Requirements (this framework)
- [x] Vulnerability Knowledge Base
- [x] Prompt Injection Lab
- [x] CI/CD Pipeline
- [ ] Incident Response Plan (TODO)
- [ ] Security Architecture Doc (TODO)

### Traceability

All requirements are traceable:

| Req ID | Source | Implementation | Test |
|--------|--------|----------------|------|
| ARC-01 | OWASP ASVS V1.2 | MFA implementation | Auth tests |
| TEN-01 | Architecture | Tenant scoping | Integration tests |

## Compliance

| Standard | Level | Target Date |
|----------|-------|-------------|
| OWASP ASVS 4.2 | L2 | Q2 2026 |
| OWASP Top 10 | All | Complete |
| SOC 2 Type II | - | Q4 2026 |
| ISO 27001 | - | Q4 2026 |

## Contributing

### Adding New Requirements

1. Update `requirements/OWASP-ASVS-Compliance.md`
2. Add tests in appropriate test file
3. Update vulnerability knowledge base
4. Document in security skill

### Reporting Vulnerabilities

1. Do NOT disclose publicly
2. Report via HackerOne or security@company.com
3. Include reproduction steps
4. Await response before disclosure

## Resources

- [OWASP ASVS 4.2](https://owasp.org/www-project-application-security-verification-standard/)
- [OWASP Top 10 2021](https://owasp.org/www-project-top-ten/)
- [OWASP AI Security](https://owasp.org/www-project-ai-security/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

## License

Internal use only. All security practices must be maintained for enterprise compliance.

---

**Remember:** Security is not a feature, it's a foundation. Build security in from day one.
