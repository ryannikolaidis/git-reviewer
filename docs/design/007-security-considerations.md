# Security Considerations

## Overview

git-reviewer handles sensitive code content, integrates with external AI services, and executes system commands. This document outlines the security considerations, threat model, and mitigation strategies implemented to ensure safe operation.

## Threat Model

### Assets to Protect

1. **Source Code**: Repository content being reviewed
2. **Configuration Data**: API keys, model settings, repository paths
3. **Review Results**: AI-generated analysis and recommendations
4. **System Resources**: Local file system, network access, processes

### Threat Actors

1. **Malicious Repositories**: Crafted git repositories designed to exploit vulnerabilities
2. **Compromised Dependencies**: Supply chain attacks through dependencies
3. **Network Attackers**: Man-in-the-middle attacks on AI service communications
4. **Local Attackers**: Users with local system access
5. **Data Exfiltration**: Unauthorized access to sensitive code or results

### Attack Vectors

1. **Command Injection**: Through git operations or configuration files
2. **Path Traversal**: Via file path parameters or git operations
3. **Template Injection**: Through custom templates or variable substitution
4. **Configuration Tampering**: Malicious configuration files
5. **Dependency Vulnerabilities**: Through third-party libraries
6. **Data Exposure**: Logging sensitive information or insecure storage

## Input Validation and Sanitization

### Git Command Safety

```python
def run_git_command(repo_path, cmd, check=True):
    """Execute git commands with security controls."""
    # Validate command structure
    if not cmd or not isinstance(cmd, list):
        raise SecurityError("Invalid git command format")

    # Whitelist allowed git commands
    ALLOWED_GIT_COMMANDS = {
        "diff", "status", "log", "show", "rev-parse", "merge-base",
        "symbolic-ref", "branch", "show-ref", "submodule"
    }

    if len(cmd) < 2 or cmd[0] != "git" or cmd[1] not in ALLOWED_GIT_COMMANDS:
        raise SecurityError(f"Git command not allowed: {cmd}")

    # Validate repository path
    repo_path = validate_repository_path(repo_path)

    try:
        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=check,
            timeout=30,  # Prevent hanging
            env=get_safe_environment()  # Controlled environment
        )
        return result
    except subprocess.TimeoutExpired:
        raise SecurityError("Git command timed out")
    except subprocess.CalledProcessError as e:
        # Sanitize error messages to prevent information disclosure
        sanitized_error = sanitize_error_message(e.stderr)
        raise GitRepositoryError(f"Git command failed: {sanitized_error}")
```

### Path Validation

```python
def validate_repository_path(repo_path):
    """Validate repository path for security."""
    path = Path(repo_path).resolve()

    # Check for path traversal attempts
    try:
        path.resolve().relative_to(Path.cwd().resolve())
    except ValueError:
        # Allow absolute paths but validate they're safe
        if not is_safe_absolute_path(path):
            raise SecurityError(f"Repository path not allowed: {path}")

    # Ensure it's actually a git repository
    if not (path / ".git").exists():
        raise SecurityError(f"Not a git repository: {path}")

    # Check path doesn't contain suspicious components
    for part in path.parts:
        if part.startswith(".") and part not in {".git", ".", ".."}:
            logger.warning(f"Suspicious path component: {part}")

    return path

def is_safe_absolute_path(path):
    """Check if absolute path is safe to access."""
    # Deny access to system directories
    FORBIDDEN_PATHS = {
        Path("/etc"), Path("/bin"), Path("/sbin"),
        Path("/usr/bin"), Path("/usr/sbin"),
        Path("/root"), Path("/home").resolve()
    }

    for forbidden in FORBIDDEN_PATHS:
        try:
            path.resolve().relative_to(forbidden)
            return False
        except ValueError:
            continue

    return True
```

### Configuration Security

```python
def load_yaml_config(config_path):
    """Load YAML configuration with security controls."""
    # Validate file path
    config_path = Path(config_path).resolve()
    validate_config_path(config_path)

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            # Use safe YAML loader to prevent code execution
            config = yaml.safe_load(f)

        if not isinstance(config, dict):
            raise ConfigurationError("Config file must contain a YAML object")

        # Validate configuration structure
        validate_config_security(config)
        return config

    except yaml.YAMLError as e:
        raise ConfigurationError(f"Invalid YAML in config file: {e}")

def validate_config_security(config):
    """Validate configuration for security issues."""
    # Check for suspicious model options
    for model in config.get("models", []):
        if "options" in model:
            validate_model_options(model["options"])

    # Validate paths
    for path_key in ["template", "output_dir"]:
        if path_key in config.get("paths", {}):
            path_value = config["paths"][path_key]
            if not is_safe_config_path(path_value):
                raise SecurityError(f"Unsafe path in configuration: {path_value}")

def validate_model_options(options):
    """Validate model options for security."""
    if not isinstance(options, list):
        return

    # Check for command injection attempts
    dangerous_patterns = [";", "&", "|", "`", "$", "$(", ">", "<", "&&", "||"]
    for option in options:
        if not isinstance(option, str):
            continue
        for pattern in dangerous_patterns:
            if pattern in option:
                logger.warning(f"Potentially dangerous option: {option}")
```

## Template Security

### Safe Variable Substitution

```python
def safe_variable_substitution(template, variables):
    """Perform safe variable substitution."""
    # Validate template content
    validate_template_security(template)

    result = template
    for var_name, var_value in variables.items():
        # Validate variable names
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', var_name):
            raise SecurityError(f"Invalid variable name: {var_name}")

        # Sanitize variable values
        sanitized_value = sanitize_template_variable(var_value)
        placeholder = f"${var_name}"
        result = result.replace(placeholder, sanitized_value)

    return result

def validate_template_security(template):
    """Validate template for security issues."""
    # Check for template injection attempts
    dangerous_patterns = [
        "{{", "}}", "<%", "%>", "${", "#{", "<!--", "-->",
        "<script", "</script>", "eval(", "exec(", "__import__"
    ]

    for pattern in dangerous_patterns:
        if pattern in template:
            logger.warning(f"Potentially dangerous template pattern: {pattern}")

def sanitize_template_variable(value):
    """Sanitize template variable values."""
    if not isinstance(value, str):
        return str(value)

    # Remove null bytes and control characters
    sanitized = value.replace('\x00', '').replace('\r', '\\r').replace('\n', '\\n')

    # Limit length to prevent DoS
    if len(sanitized) > 1_000_000:  # 1MB limit
        sanitized = sanitized[:1_000_000] + "... (truncated for security)"

    return sanitized
```

### Template Loading Security

```python
def load_template_safely(template_path):
    """Load template with security controls."""
    # Resolve and validate path
    template_path = Path(template_path).resolve()

    # Ensure template is in allowed location
    if not is_allowed_template_path(template_path):
        raise SecurityError(f"Template path not allowed: {template_path}")

    # Check file size to prevent DoS
    if template_path.stat().st_size > 10_000_000:  # 10MB limit
        raise SecurityError("Template file too large")

    # Load with encoding validation
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        raise SecurityError("Template file contains invalid encoding")

    return yaml.safe_load(content)

def is_allowed_template_path(path):
    """Check if template path is in allowed location."""
    # Allow templates in package directory
    package_dir = Path(__file__).parent
    try:
        path.relative_to(package_dir)
        return True
    except ValueError:
        pass

    # Allow templates in current working directory tree
    try:
        path.relative_to(Path.cwd())
        return True
    except ValueError:
        pass

    # Allow user-specified template directories
    allowed_dirs = get_allowed_template_directories()
    for allowed_dir in allowed_dirs:
        try:
            path.relative_to(allowed_dir)
            return True
        except ValueError:
            continue

    return False
```

## Data Protection

### Sensitive Data Handling

```python
class SecureDataHandler:
    """Handle sensitive data securely."""

    def __init__(self):
        self.temp_files = []
        self.sensitive_patterns = [
            re.compile(r'password\s*[=:]\s*\S+', re.IGNORECASE),
            re.compile(r'api[_-]?key\s*[=:]\s*\S+', re.IGNORECASE),
            re.compile(r'secret\s*[=:]\s*\S+', re.IGNORECASE),
            re.compile(r'token\s*[=:]\s*\S+', re.IGNORECASE),
        ]

    def process_diff_safely(self, diff_content):
        """Process git diff while protecting sensitive data."""
        # Scan for sensitive patterns
        sensitive_lines = []
        lines = diff_content.split('\n')

        for i, line in enumerate(lines):
            for pattern in self.sensitive_patterns:
                if pattern.search(line):
                    sensitive_lines.append(i)
                    logger.warning(f"Potential sensitive data at line {i}")

        # Redact sensitive content
        if sensitive_lines:
            return self.redact_sensitive_lines(lines, sensitive_lines)

        return diff_content

    def redact_sensitive_lines(self, lines, sensitive_lines):
        """Redact sensitive content from lines."""
        redacted_lines = lines.copy()
        for line_no in sensitive_lines:
            original_line = lines[line_no]
            # Keep diff markers but redact content
            if original_line.startswith(('+', '-', ' ')):
                prefix = original_line[0]
                redacted_lines[line_no] = f"{prefix}[REDACTED: potentially sensitive data]"
            else:
                redacted_lines[line_no] = "[REDACTED: potentially sensitive data]"

        return '\n'.join(redacted_lines)

    def create_secure_temp_file(self, content):
        """Create temporary file with secure permissions."""
        fd, path = tempfile.mkstemp(prefix="git-reviewer-", suffix=".tmp")
        try:
            # Set secure permissions (owner only)
            os.chmod(path, 0o600)

            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(content)

            self.temp_files.append(Path(path))
            return Path(path)
        except Exception:
            os.close(fd)
            if os.path.exists(path):
                os.unlink(path)
            raise

    def cleanup(self):
        """Securely clean up temporary files."""
        for temp_file in self.temp_files:
            try:
                if temp_file.exists():
                    # Overwrite file content before deletion
                    with open(temp_file, 'w') as f:
                        f.write('0' * temp_file.stat().st_size)
                    temp_file.unlink()
            except Exception as e:
                logger.error(f"Failed to clean up temp file {temp_file}: {e}")

        self.temp_files.clear()
```

### Logging Security

```python
class SecureLogger:
    """Secure logging that avoids sensitive data."""

    def __init__(self):
        self.sensitive_patterns = [
            re.compile(r'(api[_-]?key|password|secret|token)\s*[=:]\s*(\S+)', re.IGNORECASE),
            re.compile(r'Bearer\s+\S+', re.IGNORECASE),
            re.compile(r'[a-zA-Z0-9+/]{20,}={0,2}', re.IGNORECASE),  # Base64-like
        ]

    def safe_log(self, level, message, *args, **kwargs):
        """Log message after removing sensitive content."""
        sanitized_message = self.sanitize_log_message(message)
        sanitized_args = [self.sanitize_log_message(str(arg)) for arg in args]

        getattr(logger, level)(sanitized_message, *sanitized_args, **kwargs)

    def sanitize_log_message(self, message):
        """Remove sensitive content from log messages."""
        if not isinstance(message, str):
            message = str(message)

        for pattern in self.sensitive_patterns:
            message = pattern.sub(r'\1=[REDACTED]', message)

        return message

# Global secure logger instance
secure_logger = SecureLogger()
```

## Network Security

### AI Service Communication

```python
def configure_nllm_security():
    """Configure nllm with security considerations."""
    # Set environment variables for secure communication
    os.environ.setdefault('REQUESTS_CA_BUNDLE', get_ca_bundle_path())
    os.environ.setdefault('CURL_CA_BUNDLE', get_ca_bundle_path())

    # Configure timeouts to prevent hanging
    os.environ.setdefault('LLM_TIMEOUT', '120')

    # Disable insecure features
    os.environ.setdefault('PYTHONHTTPSVERIFY', '1')

def get_safe_environment():
    """Get environment variables safe for subprocess execution."""
    # Start with minimal environment
    safe_env = {
        'PATH': os.environ.get('PATH', ''),
        'HOME': os.environ.get('HOME', ''),
        'USER': os.environ.get('USER', ''),
        'LANG': os.environ.get('LANG', 'en_US.UTF-8'),
    }

    # Add necessary AI service variables
    ai_env_vars = ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GOOGLE_API_KEY']
    for var in ai_env_vars:
        if var in os.environ:
            safe_env[var] = os.environ[var]

    # Add TLS/SSL configuration
    tls_vars = ['REQUESTS_CA_BUNDLE', 'CURL_CA_BUNDLE', 'SSL_CERT_FILE']
    for var in tls_vars:
        if var in os.environ:
            safe_env[var] = os.environ[var]

    return safe_env
```

## Error Handling Security

### Information Disclosure Prevention

```python
def sanitize_error_message(error_msg):
    """Sanitize error messages to prevent information disclosure."""
    if not error_msg:
        return "Unknown error"

    # Remove absolute paths
    sanitized = re.sub(r'/[a-zA-Z0-9_./\-]+', '[PATH]', error_msg)

    # Remove usernames
    sanitized = re.sub(r'/Users/[^/\s]+', '/Users/[USER]', sanitized)
    sanitized = re.sub(r'/home/[^/\s]+', '/home/[USER]', sanitized)

    # Remove potential secrets
    sanitized = re.sub(r'[a-zA-Z0-9+/]{20,}={0,2}', '[REDACTED]', sanitized)

    # Limit length
    if len(sanitized) > 500:
        sanitized = sanitized[:500] + "... [truncated]"

    return sanitized

class SecurityError(Exception):
    """Security-related errors that should be handled carefully."""
    def __init__(self, message, log_full_error=False):
        super().__init__(message)
        if log_full_error:
            secure_logger.safe_log('error', f"Security error: {message}")
        else:
            secure_logger.safe_log('warning', "Security error occurred")
```

## Dependency Security

### Supply Chain Protection

```python
def validate_dependencies():
    """Validate critical dependencies for security."""
    critical_deps = ['nllm', 'typer', 'pyyaml', 'rich']

    for dep in critical_deps:
        try:
            module = importlib.import_module(dep)
            version = getattr(module, '__version__', 'unknown')

            # Check against known vulnerabilities (simplified)
            if is_vulnerable_version(dep, version):
                logger.warning(f"Potentially vulnerable dependency: {dep} {version}")

        except ImportError:
            logger.error(f"Critical dependency not found: {dep}")

def is_vulnerable_version(package, version):
    """Check if package version has known vulnerabilities."""
    # This would integrate with vulnerability databases
    # For now, just a placeholder
    return False
```

## Security Configuration

### Default Security Settings

```python
DEFAULT_SECURITY_CONFIG = {
    "max_file_size": 10_000_000,  # 10MB
    "max_diff_size": 1_000_000,   # 1MB
    "command_timeout": 30,         # 30 seconds
    "temp_file_cleanup": True,
    "sensitive_data_detection": True,
    "path_validation": True,
    "template_security": True,
}

def get_security_config():
    """Get current security configuration."""
    config = DEFAULT_SECURITY_CONFIG.copy()

    # Allow override via environment variables
    for key, default_value in config.items():
        env_key = f"GIT_REVIEWER_SECURITY_{key.upper()}"
        if env_key in os.environ:
            if isinstance(default_value, bool):
                config[key] = os.environ[env_key].lower() in ('true', '1', 'yes')
            elif isinstance(default_value, int):
                try:
                    config[key] = int(os.environ[env_key])
                except ValueError:
                    logger.warning(f"Invalid value for {env_key}: {os.environ[env_key]}")

    return config
```

## Security Testing

### Security Test Cases

```python
class TestSecurity:
    def test_path_traversal_prevention(self):
        """Test prevention of path traversal attacks."""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/shadow",
            "../../../../root/.ssh/id_rsa"
        ]

        for path in malicious_paths:
            with pytest.raises(SecurityError):
                validate_repository_path(path)

    def test_command_injection_prevention(self):
        """Test prevention of command injection."""
        malicious_commands = [
            ["git", "diff; rm -rf /"],
            ["git", "diff", "`rm -rf /`"],
            ["git", "diff", "$(whoami)"],
            ["git", "diff", "&& cat /etc/passwd"]
        ]

        for cmd in malicious_commands:
            with pytest.raises(SecurityError):
                run_git_command("/tmp", cmd)

    def test_template_injection_prevention(self):
        """Test prevention of template injection."""
        malicious_templates = [
            "{{7*7}}",
            "<%eval('rm -rf /')%>",
            "${java.lang.Runtime}",
            "<!--#exec cmd=\"whoami\"-->"
        ]

        for template in malicious_templates:
            # Should log warning but not execute
            result = safe_variable_substitution(template, {})
            assert "rm" not in result
            assert "eval" not in result

    def test_sensitive_data_redaction(self):
        """Test redaction of sensitive data."""
        sensitive_content = """
        api_key = sk-1234567890abcdef
        password: super_secret_password
        token=abc123def456
        """

        handler = SecureDataHandler()
        redacted = handler.process_diff_safely(sensitive_content)

        assert "sk-1234567890abcdef" not in redacted
        assert "super_secret_password" not in redacted
        assert "abc123def456" not in redacted
        assert "[REDACTED" in redacted
```

## Security Monitoring

### Security Events

```python
def log_security_event(event_type, details, severity="medium"):
    """Log security-related events."""
    secure_logger.safe_log('warning', f"Security event: {event_type}")

    # Could integrate with SIEM or monitoring systems
    event_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "severity": severity,
        "details": sanitize_log_message(details)
    }

    # Write to security log
    with open("/var/log/git-reviewer-security.log", "a") as f:
        json.dump(event_data, f)
        f.write("\n")
```

This comprehensive security framework ensures git-reviewer operates safely while handling sensitive source code and integrating with external AI services. Regular security reviews and updates to these measures are essential as the threat landscape evolves.