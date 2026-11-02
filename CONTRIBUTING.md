
# Contributing to MELTYMON AI OS

Thank you for your interest in contributing to MELTYMON AI OS!

MELTYMON AI OS is an open-source project focused on building a modular, local-first AI orchestration platform.

The project is currently in an early development stage. Contributions, bug reports, ideas, documentation improvements, and constructive feedback are welcome.

This document explains how to contribute.

---

## Before You Start

Please keep in mind:

- The project is under active development.
- Some modules are architectural scaffolding and are not fully implemented.
- Interfaces and internal architecture may change.
- Reliability, modularity, and maintainability are important design goals.

For larger changes, architectural changes, or new subsystems, please open an issue or start a discussion before implementing the work.

This helps avoid duplicated effort and makes it easier to agree on the intended design.

---

## Ways to Contribute

There are several ways to help:

- Report bugs.
- Suggest new features.
- Improve documentation.
- Add or improve automated tests.
- Improve monitoring and diagnostics.
- Implement additional hardware backends.
- Extend AI backend integrations.
- Improve configuration and validation.
- Help with architecture and code reviews.

You do not need to implement a complete feature to make a useful contribution.

---

## Development Environment

### Requirements

- Python 3.11 or newer.
- Git.
- Linux is the primary development environment.
- Ollama is required for testing the local AI backend against a running service.

### Clone the Repository

```fish
git clone https://github.com/meltymon/meltymon-ai-os.git
cd meltymon-ai-os
```



### Create a Virtual Environment

```fish
python -m venv .venv
source .venv/bin/activate.fish
```

### Install the Project

```fish
python -m pip install -e .
```

Install development and test dependencies:

```fish
python -m pip install -e ".[test]"
```

---

## Development Guidelines

Please follow these general principles:

### 1. Keep Changes Focused

- Prefer small, clearly scoped changes.
- Avoid unrelated refactoring in feature or bug-fix contributions.
- Keep modules focused on their responsibilities.
- Avoid unnecessary dependencies.

### 2. Preserve Existing Behavior

- Do not silently remove existing functionality.
- Avoid destructive changes to user data or configuration.
- Make changes to public interfaces deliberately.
- Consider backward compatibility when changing existing APIs.

### 3. Handle Errors Explicitly

- Do not silently swallow unexpected exceptions.
- Isolate failures where possible.
- Provide useful error information.
- Do not allow one unavailable hardware component to unnecessarily break unrelated monitoring components.

### 4. Keep the Platform Local-First

- Prefer local services and local model execution.
- Do not introduce external network dependencies without a clear reason.
- Keep service endpoints and configuration explicit.
- Avoid exposing local APIs beyond their intended network interface.

### 5. Write Maintainable Python

- Use clear names and focused functions.
- Add type hints where appropriate.
- Document non-obvious behavior.
- Validate external input and configuration.
- Avoid unnecessary complexity.

---

## Testing

Automated tests are an important part of the project.

Before submitting a contribution, run the relevant tests.

Run the complete test suite:

```fish
pytest -q
```

Run an individual test module:

```fish
pytest -q tests/test_monitoring_service.py
```

Run tests with coverage:

```fish
pytest --cov=meltymon_ai_os --cov-report=term-missing
```

Check the patch for whitespace errors:

```fish
git diff --check
```

If a change affects existing functionality, please add or update tests accordingly.

Tests should use mocks and temporary resources where possible. They should not modify the host system or depend on specific hardware unless the test is explicitly designed as a hardware integration test.

If a test requires a running Ollama service or specific hardware, document that requirement clearly.

---

## Pull Request Process

1. Fork the repository.
2. Create a branch for your change.
3. Implement the change.
4. Add or update tests.
5. Run the relevant tests.
6. Run `git diff --check`.
7. Commit your changes with a descriptive commit message.
8. Open a pull request describing the change.

Please include the following information in your pull request:

- What problem does the change solve?
- What has been changed?
- Why is the change necessary?
- Which tests were added or updated?
- Have the relevant tests been executed?
- Are there any known limitations or compatibility considerations?

Keep pull requests focused and reasonably small where possible.

---

## Commit Messages

Please use clear, descriptive commit messages.

Examples:

```text
feat: add NVIDIA GPU monitoring backend
fix: handle missing GPU temperature telemetry
test: extend multi-GPU monitoring coverage
docs: improve installation instructions
refactor: simplify monitoring service
```

The prefixes are recommendations to keep project history readable.

---

## Reporting Bugs

When reporting a bug, please include:

- A short and descriptive title.
- Steps to reproduce the problem.
- Expected behavior.
- Actual behavior.
- Relevant error messages or logs.
- Python version.
- Linux distribution and kernel version, where relevant.
- Relevant hardware information, where relevant.

Please remove passwords, API keys, tokens, personal information, and other sensitive data from logs before sharing them.

---

## Feature Requests

Feature requests are welcome.

Please describe:

- The problem or use case.
- The expected behavior.
- Why the feature would be useful.
- Any relevant technical considerations.

For larger architectural changes, please discuss the proposal before starting implementation.

---

## Licensing

By intentionally submitting a contribution for inclusion in MELTYMON AI OS, you agree that your contribution is provided under the project's Apache License, Version 2.0, unless a separate written agreement applies.

You retain the copyright to your original contributions.

Please only submit code and other materials that you have the right to contribute.

If your contribution includes third-party code or assets, identify their origin and applicable license.

---

## Community and Conduct

Please be respectful and constructive.

We welcome different levels of experience and backgrounds. Technical discussions should focus on ideas, implementation quality, reliability, and maintainability.

Harassment, discrimination, personal attacks, and deliberately disruptive behavior are not acceptable.

---

## Thank You

Every contribution helps make MELTYMON AI OS better.

Whether you report a bug, improve documentation, write tests, suggest an architectural improvement, or implement a feature, your time and effort are appreciated.

Thank you for helping build MELTYMON AI OS!
