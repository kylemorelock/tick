# Checklist schema

Checklists are YAML files with a top-level `checklist` object.

```yaml
checklist:
  name: "Web Application Security Audit"
  version: "1.0.0"
  domain: "web"
  metadata:
    author: "Security Team"
    tags: ["security", "owasp"]
  variables:
    environment:
      prompt: "Environment"
      options: ["dev", "staging", "prod"]
  sections:
    - name: "Authentication"
      items:
        - id: "auth-001"
          check: "Verify password complexity requirements"
          severity: "critical"
          evidence_required: true
```

## Fields

- `metadata` is optional and supports `author`, `tags`, and `estimated_time`.
- `variables` are prompted at runtime and are used in conditions.
- `sections` contain `items` with optional `condition` and `matrix` data.
