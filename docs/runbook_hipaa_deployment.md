# Deployment Runbook: HIPAA Compliance (Sprint 1B)

**Date:** 2025-10-14  
**Author:** HealthFlow Security Team  
**Version:** 1.0

---

## 1. Overview

This runbook provides step-by-step instructions for deploying the HIPAA compliance features from Sprint 1B, including:
- Field-level encryption for PHI
- Comprehensive audit logging
- Database migration for existing data

**Estimated Deployment Time:** 1-2 hours (plus data migration time)  
**Downtime Expected:** Yes (during database migration)

---

## 2. Pre-Deployment Checklist

| Status | Task | Owner | Notes |
|--------|------|-------|-------|
| [ ] | **Database Backup** | DBA | Full backup of production database (critical!) |
| [ ] | **Code Merged** | Dev Lead | PRs #24, #25, and #26 (Sprint 1B) merged to main |
| [ ] | **Environment Variables** | DevOps | `ENCRYPTION_MASTER_KEY` set in production |
| [ ] | **Migration Confirmation** | DevOps | `MIGRATION_BACKUP_CONFIRMED=true` set |
| [ ] | **Stakeholder Communication** | Product | Notify stakeholders of planned downtime |
| [ ] | **Rollback Plan** | Dev Lead | Rollback plan reviewed and ready |
| [ ] | **Monitoring Ready** | DevOps | Monitoring dashboards open and ready |

---

## 3. Deployment Steps

### Phase 1: Announce Maintenance Window (5 mins)
1. Post maintenance notice on status page
2. Announce in internal communication channels

### Phase 2: Scale Down Application (10 mins)
1. Scale down web servers to 0 instances
2. Ensure no active connections to the database

### Phase 3: Deploy New Code (15 mins)
1. Deploy the latest `main` branch to production servers
2. **DO NOT** scale up yet

### Phase 4: Run Database Migration (Variable Time)
1. **CRITICAL:** Ensure database backup is complete and verified
2. Open a shell on one of the application servers
3. Run the Alembic migration:
   ```bash
   export FLASK_APP=src/main.py
   export MIGRATION_BACKUP_CONFIRMED=true
   flask db upgrade
   ```
4. **Monitor logs closely** for progress and errors
5. **Estimated Time:** 5 minutes per 10,000 records

### Phase 5: Post-Migration Verification (15 mins)
1. Connect to the production database
2. Run verification queries:
   ```sql
   -- Verify encrypted fields are populated
   SELECT COUNT(*) FROM prescriptions WHERE patient_name IS NOT NULL;
   
   -- Verify plaintext fields are gone
   -- This should fail
   SELECT patient_name_plaintext FROM prescriptions LIMIT 1;
   ```
3. Check for any errors in the migration logs

### Phase 6: Scale Up Application (10 mins)
1. Scale web servers back to normal capacity
2. Monitor application logs for startup errors

### Phase 7: Functional Testing (15 mins)
1. **Login/Logout:** Verify authentication works
2. **Prescription Upload:** Upload a new prescription
3. **PHI Access:** View a prescription and verify data is visible (decrypted)
4. **Audit Log Check:** Verify new audit logs are being created for these actions

### Phase 8: Monitoring (30 mins)
1. Monitor error rates, latency, and CPU/memory usage
2. Check for any unusual spikes or alerts
3. Ensure no new exceptions are being logged

### Phase 9: Announce Completion (5 mins)
1. Remove maintenance notice from status page
2. Announce completion in internal channels

---

## 4. Rollback Plan

**Trigger:**
- Migration failure that cannot be resolved in 30 minutes
- Critical application functionality broken post-deployment
- Unacceptable performance degradation

**Steps:**
1. **Announce Rollback:** Notify stakeholders of rollback
2. **Scale Down:** Scale application to 0
3. **Restore Database:** Restore database from pre-deployment backup (CRITICAL)
4. **Redeploy Previous Version:** Deploy the previous stable version of the code
5. **Scale Up:** Scale application back to normal capacity
6. **Verify:** Perform functional testing on the rolled-back version
7. **Post-Mortem:** Conduct a post-mortem to analyze the failure

---

## 5. Emergency Contacts

| Role | Name | Contact |
|------|------|---------|
| Dev Lead | [Name] | [Phone/Email] |
| DevOps Lead | [Name] | [Phone/Email] |
| DBA | [Name] | [Phone/Email] |
| Product Manager | [Name] | [Phone/Email] |

---

## 6. Communication Templates

### Maintenance Start
**Subject:** Planned Maintenance: HealthFlow Security Upgrade

**Body:**
HealthFlow will be undergoing planned maintenance on [Date] at [Time] for a critical security upgrade. We expect approximately [X] hours of downtime. We will notify you once the maintenance is complete.

### Maintenance Complete
**Subject:** Maintenance Complete: HealthFlow Security Upgrade

**Body:**
The planned maintenance for our security upgrade is now complete. All systems are back online. Thank you for your patience.

