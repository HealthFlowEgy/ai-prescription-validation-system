# GitHub Secrets Configuration Checklist

## Required Secrets for CI/CD Pipeline

To ensure the CI/CD pipeline runs successfully, the following secrets must be configured in your GitHub repository settings.

### How to Add Secrets

1. Go to your repository: https://github.com/HealthFlowEgy/ai-prescription-validation-system
2. Click on **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret from the list below

---

## 🔐 Required Secrets

### Application Secrets

| Secret Name | Description | Example Value | Required |
|-------------|-------------|---------------|----------|
| `JWT_SECRET_KEY` | Secret key for JWT token generation | `your-secret-key-min-32-chars-long` | ✅ Yes |
| `ENCRYPTION_KEY` | Fernet key for PHI encryption (44 chars base64) | `your-fernet-key-44-chars-base64==` | ✅ Yes |
| `DATABASE_URL` | PostgreSQL connection string for production | `postgresql://user:pass@host:5432/db` | ⚠️ Production only |
| `REDIS_URL` | Redis connection string for production | `redis://host:6379/0` | ⚠️ Production only |

### Docker Registry Secrets

| Secret Name | Description | Example Value | Required |
|-------------|-------------|---------------|----------|
| `DOCKER_USERNAME` | Docker Hub username | `healthflow` | ⚠️ If using Docker Hub |
| `DOCKER_PASSWORD` | Docker Hub password/token | `dckr_pat_xxxxx` | ⚠️ If using Docker Hub |

### Kubernetes Deployment Secrets

| Secret Name | Description | Example Value | Required |
|-------------|-------------|---------------|----------|
| `KUBE_CONFIG_STAGING` | Base64-encoded kubeconfig for staging | `<base64-encoded-config>` | ⚠️ Staging only |
| `KUBE_CONFIG_PRODUCTION` | Base64-encoded kubeconfig for production | `<base64-encoded-config>` | ⚠️ Production only |

### AWS Secrets (if using AWS)

| Secret Name | Description | Example Value | Required |
|-------------|-------------|---------------|----------|
| `AWS_ACCESS_KEY_ID` | AWS access key for staging | `AKIAIOSFODNN7EXAMPLE` | ⚠️ If using AWS |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key for staging | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` | ⚠️ If using AWS |
| `AWS_ACCESS_KEY_ID_PROD` | AWS access key for production | `AKIAIOSFODNN7EXAMPLE` | ⚠️ If using AWS |
| `AWS_SECRET_ACCESS_KEY_PROD` | AWS secret key for production | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` | ⚠️ If using AWS |

### Notification Secrets

| Secret Name | Description | Example Value | Required |
|-------------|-------------|---------------|----------|
| `SLACK_WEBHOOK` | Slack webhook URL for staging notifications | `https://hooks.slack.com/services/xxx` | ⚠️ Optional |
| `SLACK_WEBHOOK_PROD` | Slack webhook URL for production notifications | `https://hooks.slack.com/services/xxx` | ⚠️ Optional |
| `EMAIL_USERNAME` | SMTP username for email notifications | `alerts@healthflow.com` | ⚠️ Optional |
| `EMAIL_PASSWORD` | SMTP password for email notifications | `your-smtp-password` | ⚠️ Optional |
| `NOTIFICATION_EMAIL` | Email address to receive failure notifications | `devops@healthflow.com` | ⚠️ Optional |

### Testing Secrets

| Secret Name | Description | Example Value | Required |
|-------------|-------------|---------------|----------|
| `TEST_USER_EMAIL` | Test user email for smoke tests | `test@healthflow.com` | ⚠️ Production tests only |
| `TEST_USER_PASSWORD` | Test user password for smoke tests | `TestPassword123!` | ⚠️ Production tests only |
| `CODECOV_TOKEN` | Codecov token for coverage reports | `xxxxx-xxxx-xxxx-xxxx-xxxxx` | ⚠️ Optional |
| `SNYK_TOKEN` | Snyk token for security scanning | `xxxxx-xxxx-xxxx-xxxx-xxxxx` | ⚠️ Optional |

---

## 🔍 How to Verify Secrets

Run this command to check which secrets are configured (requires admin access):

```bash
gh secret list --repo HealthFlowEgy/ai-prescription-validation-system
```

**Note:** You need repository admin permissions to view secrets.

---

## 🛠️ Generating Required Secrets

### JWT Secret Key

```bash
# Generate a secure random key (32+ characters)
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Encryption Key (Fernet)

```bash
# Generate a Fernet key (44 characters base64)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Base64 Encode Kubeconfig

```bash
# Encode your kubeconfig file
cat ~/.kube/config | base64 -w 0
```

---

## ⚠️ Important Notes

1. **Never commit secrets to the repository** - Always use GitHub Secrets
2. **Rotate secrets regularly** - Update secrets every 90 days for security
3. **Use different secrets for staging and production** - Never reuse production secrets in staging
4. **Test secrets after adding** - Trigger a workflow run to verify secrets work
5. **Document secret rotation** - Keep track of when secrets were last updated

---

## 📧 Reducing Email Notifications

If you're receiving too many email notifications from failed workflows:

### Option 1: GitHub Notification Settings (Recommended)

1. Go to: https://github.com/settings/notifications
2. Scroll to **Actions**
3. Uncheck **Email** notifications
4. Keep **Web and Mobile** notifications enabled

### Option 2: Use Slack Instead

1. Create a Slack webhook: https://api.slack.com/messaging/webhooks
2. Add the webhook URL to `SLACK_WEBHOOK` secret
3. Workflows will send notifications to Slack instead of email

### Option 3: Filter Notifications in Email

Create an email filter to automatically archive or label GitHub Actions emails:

**Gmail Filter:**
- From: `notifications@github.com`
- Subject: `[HealthFlowEgy/ai-prescription-validation-system]`
- Action: Skip Inbox, Apply Label "GitHub CI/CD"

---

## 🎯 Quick Start Checklist

For a minimal working CI/CD pipeline, you only need:

- [ ] `JWT_SECRET_KEY` - Generate with command above
- [ ] `ENCRYPTION_KEY` - Generate with command above
- [ ] Update GitHub notification settings to reduce email spam

All other secrets are optional and only needed for specific features (deployment, notifications, etc.).

---

**Last Updated:** December 8, 2025

