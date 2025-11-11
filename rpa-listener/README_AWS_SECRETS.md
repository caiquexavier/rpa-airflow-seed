# AWS Secrets Manager Integration

The rpa-listener now automatically loads AWS credentials from AWS Secrets Manager before running Robot Framework tests.

## How It Works

1. When a message is received, the handler loads secrets from AWS Secrets Manager
2. Secrets are loaded into the environment variables
3. Robot Framework subprocess inherits these environment variables
4. S3 uploads use the credentials from Secrets Manager

## Configuration

### Environment Variables

The following environment variables control secret loading:

- `AWS_SECRET_NAME` - Name of the secret in AWS Secrets Manager (default: `dev/rpa-airflow`)
- `AWS_REGION` - AWS region where the secret is stored (default: `eu-north-1`)

### Required Secrets in AWS Secrets Manager

The secret must contain the following keys (as JSON):

```json
{
  "AWS_ACCESS_KEY_ID": "your-access-key",
  "AWS_SECRET_ACCESS_KEY": "your-secret-key",
  "AWS_DEFAULT_REGION": "us-east-1",
  "AWS_S3_BUCKET": "your-bucket-name"
}
```

## AWS Credentials for Secrets Manager Access

The listener needs AWS credentials to access Secrets Manager. These can be provided via:

1. **Environment Variables** (for local development):
   ```powershell
   $env:AWS_ACCESS_KEY_ID = "your-key"
   $env:AWS_SECRET_ACCESS_KEY = "your-secret"
   $env:AWS_DEFAULT_REGION = "eu-north-1"
   ```

2. **AWS CLI Configuration**:
   ```bash
   aws configure
   ```

3. **IAM Role** (for EC2/ECS/Lambda):
   - Attach IAM role with `secretsmanager:GetSecretValue` permission

## IAM Permissions Required

The IAM user/role needs the following permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:eu-north-1:*:secret:dev/rpa-airflow-*"
    }
  ]
}
```

## Behavior

### Automatic Loading

By default, secrets are loaded automatically before each Robot Framework execution. This can be disabled by setting `load_aws_secrets=False` in the handler.

### Fallback Behavior

If secret loading fails:
- A warning is logged
- The process continues with existing environment variables
- Robot Framework will fail if AWS credentials are missing

### Environment Variable Priority

1. **Existing environment variables** (highest priority)
   - If a variable is already set, it won't be overwritten by secrets
2. **AWS Secrets Manager**
   - Loaded if not already in environment
3. **Missing variables**
   - Warning logged if required AWS variables are missing

## Testing

To test secret loading:

```python
from rpa_listener.src.utils.aws_secrets import load_aws_secrets_to_environment

# Load secrets
secrets = load_aws_secrets_to_environment(
    secret_name="dev/rpa-airflow",
    region="eu-north-1"
)

# Verify
import os
print(f"AWS_ACCESS_KEY_ID: {os.getenv('AWS_ACCESS_KEY_ID')[:8]}...")
print(f"AWS_S3_BUCKET: {os.getenv('AWS_S3_BUCKET')}")
```

## Troubleshooting

### Error: "Secret not found"

- Verify the secret name is correct
- Check the AWS region
- Ensure you have access to the secret

### Error: "Access denied"

- Check IAM permissions for `secretsmanager:GetSecretValue`
- Verify AWS credentials are configured
- Check if the secret exists in the specified region

### Warning: "Missing AWS environment variables"

- Secrets were not loaded successfully
- Check secret contains required keys: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_BUCKET`
- Verify secret is in JSON format

## Disabling Secret Loading

To disable automatic secret loading (use environment variables only):

Modify the handler call to set `load_aws_secrets=False`:

```python
run_robot_tests(
    project_path,
    robot_exe,
    tests_path,
    results_dir,
    message_data,
    load_aws_secrets=False  # Disable secret loading
)
```

## Security Notes

- Secrets are loaded into process memory only
- Secrets are NOT logged (only key names are logged)
- Environment variables are passed to subprocess securely
- Consider using IAM roles instead of access keys when possible

