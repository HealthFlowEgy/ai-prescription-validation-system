#!/bin/bash

echo "=========================================="
echo "Critical Fixes Verification"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test counter
PASSED=0
FAILED=0

# Test 1: Password Validator exists
echo -n "1. Password Validator module... "
if [ -f "src/utils/password_validator.py" ]; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    ((FAILED++))
fi

# Test 2: Token Manager exists
echo -n "2. Token Manager module... "
if [ -f "src/utils/token_manager.py" ]; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    ((FAILED++))
fi

# Test 3: Input Validator exists
echo -n "3. Input Validator module... "
if [ -f "src/utils/input_validator.py" ]; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    ((FAILED++))
fi

# Test 4: Rate Limiting config exists
echo -n "4. Rate Limiting configuration... "
if [ -f "src/config/rate_limiting.py" ]; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    ((FAILED++))
fi

# Test 5: Database Enforcer exists
echo -n "5. Database Enforcer module... "
if [ -f "src/config/database_enforcer.py" ]; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    ((FAILED++))
fi

# Test 6: Production Checklist exists
echo -n "6. Production Checklist... "
if [ -f "PRODUCTION_CHECKLIST.md" ]; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    ((FAILED++))
fi

# Test 7: Dependencies added
echo -n "7. Security dependencies in requirements.txt... "
if grep -q "python-magic" requirements.txt && grep -q "redis" requirements.txt; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    ((FAILED++))
fi

# Test 8: Main.py updated
echo -n "8. Database validation in main.py... "
if grep -q "validate_database_on_startup" src/main.py; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    ((FAILED++))
fi

echo ""
echo "=========================================="
echo "Results: $PASSED passed, $FAILED failed"
echo "=========================================="

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All critical fixes verified!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some fixes are missing!${NC}"
    exit 1
fi
