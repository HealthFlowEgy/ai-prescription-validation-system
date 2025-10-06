
# Integration Verification Report

**Generated:** 2025-10-06 17:24:03  
**Duration:** 2.14 seconds  
**Status:** ❌ FAILED

---

## Summary

| Metric | Value |
|--------|-------|
| Total Checks | 18 |
| Passed | 16 (88.9%) |
| Failed | 2 |
| Warnings | 0 |

---

## Passed Checks ✅

- **Configuration Files**: All config files present
- **Service Files**: All service files present
- **Route Files**: All route files present
- **Utility Files**: All utility files present
- **Migration Files**: Migration files present
- **Docker Files**: All Docker files present
- **Documentation**: All documentation present
- **Auth Service Import**: Auth service imports successfully
- **Monitoring Service Import**: Monitoring service imports successfully
- **Error Handlers Import**: Error handlers import successfully
- **Routes Import**: Route blueprints import successfully
- **Password Hashing**: Password hashing works correctly
- **JWT Tokens**: JWT token generation and decoding works
- **User Model**: User model has all required fields and methods
- **Database Config**: Database config works: sqlite:///data/development.db...
- **Metrics Collection**: Metrics collection works (CPU: 0.2%)

---

## Failed Checks ❌

- **Application Factory**: Error: Table 'prescriptions' is already defined for this MetaData instance.  Specify 'extend_existing=True' to redefine options and columns on an existing Table object.
- **Blueprints Registered**: Error: Table 'prescriptions' is already defined for this MetaData instance.  Specify 'extend_existing=True' to redefine options and columns on an existing Table object.

---

## Conclusion

❌ **2 check(s) failed.** Please review the failed checks above and fix the issues.

**Recommended Actions:**
1. Review error messages
2. Check file paths and imports
3. Verify environment variables
4. Re-run verification after fixes
