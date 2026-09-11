# Perception Production Privacy Release Checklist

## Application

- [ ] Public schemas audited.
- [ ] Private account fields excluded from public contracts.
- [ ] Owner-only analytics authorization tested.
- [ ] Observer/creator metric isolation tested.
- [ ] Minimum sample threshold tested.
- [ ] City-level aggregate suppression verified.
- [ ] AI payload identity minimization tested.
- [ ] External AI processing is opt-in.
- [ ] Production API docs disabled.
- [ ] API responses no-store.

## Infrastructure

- [ ] Production DB private.
- [ ] Redis private.
- [ ] Storage access reviewed.
- [ ] HTTPS/TLS everywhere.
- [ ] Secrets outside Git.
- [ ] Backups protected.
- [ ] Restore tested.
- [ ] Admin access protected.
- [ ] CI/CD least privilege.

## Governance

- [ ] Privacy notice published.
- [ ] Terms published.
- [ ] Data retention/deletion policy defined.
- [ ] Data-subject rights process defined.
- [ ] Processor inventory maintained.
- [ ] Required processor agreements completed.
- [ ] AI processing disclosure completed.
- [ ] Incident response procedure tested.

## Final decision

Application controls passing does **not** by itself mean the product is legally or operationally privacy-complete. The release owner must review the infrastructure and governance sections before production launch.
