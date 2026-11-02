# Security Policy

## Supported Versions

MELTYMON AI OS is currently in early development.

At this stage, security fixes are generally applied to the latest development version on the `main` branch.

No stable release versions are currently supported.

## Reporting a Vulnerability

We take security reports seriously.

If you discover a potential security vulnerability, please do not disclose it through public GitHub Issues or Discussions.

Use GitHub's private vulnerability reporting feature:

1. Open the repository on GitHub.
2. Navigate to the Security tab.
3. Select "Report a vulnerability".
4. Provide a detailed description of the issue.

If private vulnerability reporting is unavailable, contact the repository maintainer through their GitHub profile. Please do not publish sensitive details publicly.

## What to Include

When reporting a vulnerability, please provide:

- A description of the vulnerability.
- The affected component or module.
- Steps to reproduce the issue.
- Potential security impact.
- Relevant logs or proof-of-concept code, if available.
- Possible mitigation or remediation suggestions.

Please avoid including real credentials, API tokens, private keys or personal data.

## Response Process

The maintainers will:

1. Review the submitted report.
2. Assess its severity and potential impact.
3. Investigate and reproduce the issue where possible.
4. Develop and test an appropriate fix.
5. Coordinate disclosure with the reporter.

Response times may vary depending on the complexity and severity of the report.

## Scope

Security reports concerning the following areas are particularly relevant:

- Local API exposure and network access.
- Authentication and authorization.
- Agent permissions and execution boundaries.
- Tool execution and command injection.
- Configuration handling and secret management.
- Ollama integration and backend communication.
- Dependency vulnerabilities.
- Data isolation and local storage.

Thank you for helping keep MELTYMON AI OS secure.
