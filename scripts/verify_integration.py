#!/usr/bin/env python3
"""
Automated Integration Verification Script

This script automatically verifies that all production enhancements
have been successfully integrated and are working correctly.

Usage:
    python scripts/verify_integration.py
    python scripts/verify_integration.py --verbose
    python scripts/verify_integration.py --report-file verification_report.md
"""

import os
import sys
import subprocess
import importlib
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import argparse

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_success(message):
    print(f"{Colors.GREEN}✅ {message}{Colors.RESET}")

def print_error(message):
    print(f"{Colors.RED}❌ {message}{Colors.RESET}")

def print_warning(message):
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.RESET}")

def print_info(message):
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.RESET}")

def print_header(message):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{message}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")


class IntegrationVerifier:
    """Automated integration verification"""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.results = {
            'passed': [],
            'failed': [],
            'warnings': [],
            'total': 0
        }
        self.start_time = datetime.now()
    
    def run_check(self, name: str, check_func) -> bool:
        """Run a single check and record result"""
        self.results['total'] += 1
        
        if self.verbose:
            print_info(f"Running: {name}")
        
        try:
            result, message = check_func()
            if result:
                self.results['passed'].append((name, message))
                print_success(f"{name}: {message}")
                return True
            else:
                self.results['failed'].append((name, message))
                print_error(f"{name}: {message}")
                return False
        except Exception as e:
            self.results['failed'].append((name, str(e)))
            print_error(f"{name}: {str(e)}")
            return False
    
    def add_warning(self, name: str, message: str):
        """Add a warning"""
        self.results['warnings'].append((name, message))
        print_warning(f"{name}: {message}")
    
    # ========================================================================
    # Phase 1: File Structure Checks
    # ========================================================================
    
    def check_config_files(self) -> Tuple[bool, str]:
        """Check if configuration files exist"""
        files = [
            'src/config/database.py',
            'src/config/production.py'
        ]
        missing = [f for f in files if not Path(f).exists()]
        if missing:
            return False, f"Missing files: {', '.join(missing)}"
        return True, "All config files present"
    
    def check_service_files(self) -> Tuple[bool, str]:
        """Check if service files exist"""
        files = [
            'src/services/auth_service.py',
            'src/services/monitoring_service.py'
        ]
        missing = [f for f in files if not Path(f).exists()]
        if missing:
            return False, f"Missing files: {', '.join(missing)}"
        return True, "All service files present"
    
    def check_route_files(self) -> Tuple[bool, str]:
        """Check if route files exist"""
        files = [
            'src/routes/auth_routes.py',
            'src/routes/health_routes.py'
        ]
        missing = [f for f in files if not Path(f).exists()]
        if missing:
            return False, f"Missing files: {', '.join(missing)}"
        return True, "All route files present"
    
    def check_util_files(self) -> Tuple[bool, str]:
        """Check if utility files exist"""
        files = [
            'src/utils/__init__.py',
            'src/utils/error_handlers.py'
        ]
        missing = [f for f in files if not Path(f).exists()]
        if missing:
            return False, f"Missing files: {', '.join(missing)}"
        return True, "All utility files present"
    
    def check_migration_files(self) -> Tuple[bool, str]:
        """Check if migration files exist"""
        files = [
            'migrations/env.py',
            'alembic.ini'
        ]
        missing = [f for f in files if not Path(f).exists()]
        if missing:
            return False, f"Missing files: {', '.join(missing)}"
        return True, "Migration files present"
    
    def check_docker_files(self) -> Tuple[bool, str]:
        """Check if Docker files exist"""
        files = [
            'Dockerfile.production',
            'gunicorn_config.py',
            'docker-entrypoint.sh',
            'docker-compose.prod.yml'
        ]
        missing = [f for f in files if not Path(f).exists()]
        if missing:
            return False, f"Missing files: {', '.join(missing)}"
        return True, "All Docker files present"
    
    def check_documentation(self) -> Tuple[bool, str]:
        """Check if documentation exists"""
        files = [
            'INTEGRATION_GUIDE.md',
            'PRODUCTION_ENHANCEMENTS_SUMMARY.md',
            'IMPLEMENTATION_REPORT.md'
        ]
        missing = [f for f in files if not Path(f).exists()]
        if missing:
            return False, f"Missing files: {', '.join(missing)}"
        return True, "All documentation present"
    
    # ========================================================================
    # Phase 2: Import Checks
    # ========================================================================
    
    def check_auth_service_import(self) -> Tuple[bool, str]:
        """Check if auth service can be imported"""
        try:
            from services.auth_service import AuthService, token_required
            return True, "Auth service imports successfully"
        except ImportError as e:
            return False, f"Import error: {str(e)}"
    
    def check_monitoring_service_import(self) -> Tuple[bool, str]:
        """Check if monitoring service can be imported"""
        try:
            from services.monitoring_service import MonitoringService, metrics_collector
            return True, "Monitoring service imports successfully"
        except ImportError as e:
            return False, f"Import error: {str(e)}"
    
    def check_error_handlers_import(self) -> Tuple[bool, str]:
        """Check if error handlers can be imported"""
        try:
            from utils.error_handlers import APIError, ValidationError, register_error_handlers
            return True, "Error handlers import successfully"
        except ImportError as e:
            return False, f"Import error: {str(e)}"
    
    def check_routes_import(self) -> Tuple[bool, str]:
        """Check if routes can be imported"""
        try:
            from routes.auth_routes import auth_bp
            from routes.health_routes import health_bp
            return True, "Route blueprints import successfully"
        except ImportError as e:
            return False, f"Import error: {str(e)}"
    
    # ========================================================================
    # Phase 3: Functionality Checks
    # ========================================================================
    
    def check_password_hashing(self) -> Tuple[bool, str]:
        """Check if password hashing works"""
        try:
            from services.auth_service import AuthService
            password = "TestPass123!"
            hashed = AuthService.hash_password(password)
            verified = AuthService.verify_password(password, hashed)
            if verified:
                return True, "Password hashing works correctly"
            else:
                return False, "Password verification failed"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def check_jwt_tokens(self) -> Tuple[bool, str]:
        """Check if JWT token generation works"""
        try:
            os.environ['JWT_SECRET_KEY'] = 'test-secret-key-for-verification'
            from services.auth_service import AuthService
            token, expiration = AuthService.generate_token(1, 'admin')
            payload = AuthService.decode_token(token)
            if payload['user_id'] == 1 and payload['role'] == 'admin':
                return True, "JWT token generation and decoding works"
            else:
                return False, "JWT payload mismatch"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def check_user_model(self) -> Tuple[bool, str]:
        """Check if User model has new fields"""
        try:
            # Try updated model first
            try:
                from models.user_updated import User
            except ImportError:
                from models.user import User
            
            # Check for required attributes
            required_attrs = ['password_hash', 'role', 'is_active']
            user = User()
            missing = [attr for attr in required_attrs if not hasattr(user, attr)]
            
            if missing:
                return False, f"Missing attributes: {', '.join(missing)}"
            
            # Check for methods
            required_methods = ['set_password', 'check_password']
            missing_methods = [m for m in required_methods if not hasattr(user, m)]
            
            if missing_methods:
                return False, f"Missing methods: {', '.join(missing_methods)}"
            
            return True, "User model has all required fields and methods"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def check_database_config(self) -> Tuple[bool, str]:
        """Check if database configuration works"""
        try:
            from config.database import DatabaseConfig
            uri = DatabaseConfig.get_database_uri('development')
            if uri:
                return True, f"Database config works: {uri[:50]}..."
            else:
                return False, "Database URI is empty"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def check_metrics_collection(self) -> Tuple[bool, str]:
        """Check if metrics collection works"""
        try:
            from services.monitoring_service import metrics_collector
            metrics = metrics_collector.get_system_metrics()
            if 'cpu_percent' in metrics and 'memory_percent' in metrics:
                return True, f"Metrics collection works (CPU: {metrics['cpu_percent']}%)"
            else:
                return False, "Metrics missing required fields"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    # ========================================================================
    # Phase 4: Application Checks
    # ========================================================================
    
    def check_app_factory(self) -> Tuple[bool, str]:
        """Check if application factory exists"""
        try:
            # Try integrated version first
            try:
                from main_integrated import create_app
            except ImportError:
                from main import create_app
            
            # Try to create app
            os.environ['SECRET_KEY'] = 'test-secret'
            os.environ['JWT_SECRET_KEY'] = 'test-jwt'
            app = create_app('development')
            
            if app:
                return True, "Application factory works correctly"
            else:
                return False, "create_app returned None"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def check_blueprints_registered(self) -> Tuple[bool, str]:
        """Check if blueprints are registered"""
        try:
            try:
                from main_integrated import app
            except ImportError:
                from main import app
            
            blueprint_names = [bp.name for bp in app.blueprints.values()]
            required = ['auth', 'health']
            missing = [bp for bp in required if bp not in blueprint_names]
            
            if missing:
                return False, f"Missing blueprints: {', '.join(missing)}"
            
            return True, f"All blueprints registered: {', '.join(blueprint_names)}"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    # ========================================================================
    # Report Generation
    # ========================================================================
    
    def generate_report(self, output_file=None):
        """Generate verification report"""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        passed = len(self.results['passed'])
        failed = len(self.results['failed'])
        warnings = len(self.results['warnings'])
        total = self.results['total']
        success_rate = (passed / total * 100) if total > 0 else 0
        
        report = f"""
# Integration Verification Report

**Generated:** {end_time.strftime('%Y-%m-%d %H:%M:%S')}  
**Duration:** {duration:.2f} seconds  
**Status:** {'✅ PASSED' if failed == 0 else '❌ FAILED'}

---

## Summary

| Metric | Value |
|--------|-------|
| Total Checks | {total} |
| Passed | {passed} ({success_rate:.1f}%) |
| Failed | {failed} |
| Warnings | {warnings} |

---

## Passed Checks ✅

"""
        for name, message in self.results['passed']:
            report += f"- **{name}**: {message}\n"
        
        if self.results['failed']:
            report += "\n---\n\n## Failed Checks ❌\n\n"
            for name, message in self.results['failed']:
                report += f"- **{name}**: {message}\n"
        
        if self.results['warnings']:
            report += "\n---\n\n## Warnings ⚠️\n\n"
            for name, message in self.results['warnings']:
                report += f"- **{name}**: {message}\n"
        
        report += f"""
---

## Conclusion

"""
        if failed == 0:
            report += "✅ **All checks passed!** The production enhancements have been successfully integrated.\n\n"
            report += "**Next Steps:**\n"
            report += "1. Set up production environment variables\n"
            report += "2. Configure PostgreSQL database\n"
            report += "3. Run database migrations\n"
            report += "4. Deploy to production\n"
        else:
            report += f"❌ **{failed} check(s) failed.** Please review the failed checks above and fix the issues.\n\n"
            report += "**Recommended Actions:**\n"
            report += "1. Review error messages\n"
            report += "2. Check file paths and imports\n"
            report += "3. Verify environment variables\n"
            report += "4. Re-run verification after fixes\n"
        
        # Print to console
        print("\n" + "="*60)
        print(report)
        print("="*60 + "\n")
        
        # Save to file if specified
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report)
            print_success(f"Report saved to: {output_file}")
        
        return failed == 0


def main():
    """Main verification function"""
    parser = argparse.ArgumentParser(description='Verify production integration')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--report-file', '-r', help='Output report file')
    args = parser.parse_args()
    
    print_header("🔍 Production Integration Verification")
    print_info(f"Starting verification at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    verifier = IntegrationVerifier(verbose=args.verbose)
    
    # Phase 1: File Structure
    print_header("Phase 1: File Structure")
    verifier.run_check("Configuration Files", verifier.check_config_files)
    verifier.run_check("Service Files", verifier.check_service_files)
    verifier.run_check("Route Files", verifier.check_route_files)
    verifier.run_check("Utility Files", verifier.check_util_files)
    verifier.run_check("Migration Files", verifier.check_migration_files)
    verifier.run_check("Docker Files", verifier.check_docker_files)
    verifier.run_check("Documentation", verifier.check_documentation)
    
    # Phase 2: Imports
    print_header("Phase 2: Import Checks")
    verifier.run_check("Auth Service Import", verifier.check_auth_service_import)
    verifier.run_check("Monitoring Service Import", verifier.check_monitoring_service_import)
    verifier.run_check("Error Handlers Import", verifier.check_error_handlers_import)
    verifier.run_check("Routes Import", verifier.check_routes_import)
    
    # Phase 3: Functionality
    print_header("Phase 3: Functionality Checks")
    verifier.run_check("Password Hashing", verifier.check_password_hashing)
    verifier.run_check("JWT Tokens", verifier.check_jwt_tokens)
    verifier.run_check("User Model", verifier.check_user_model)
    verifier.run_check("Database Config", verifier.check_database_config)
    verifier.run_check("Metrics Collection", verifier.check_metrics_collection)
    
    # Phase 4: Application
    print_header("Phase 4: Application Checks")
    verifier.run_check("Application Factory", verifier.check_app_factory)
    verifier.run_check("Blueprints Registered", verifier.check_blueprints_registered)
    
    # Generate report
    print_header("Generating Report")
    success = verifier.generate_report(args.report_file)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
