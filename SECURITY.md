# Security policy

## Reporting a vulnerability

Please do not open a public issue for a security problem. Use GitHub's private
security advisory flow:

```text
https://github.com/Koustubh12345/TenSeiAi/security/advisories/new
```

Include:

- the affected version or commit,
- a minimal reproduction,
- the impact you believe is possible,
- any suggested fix or mitigation.

You will receive an acknowledgement as soon as practical. Please allow time for
a fix and coordinated disclosure before publishing details.

## Supported versions

Security fixes are applied to the latest release line. Older model snapshots
and forks are not supported.

## Local-server security

TenSeiAi includes a local HTTP server for the web UI and API. It is designed
for a single trusted user on `127.0.0.1`:

- There is no authentication or authorization.
- CORS is permissive for local development.
- Request bodies are not rate-limited.
- The server is not hardened for exposure to the public internet.

Do not bind the server to `0.0.0.0` on an untrusted network. If you need remote
access, put it behind a reverse proxy with TLS, authentication, request limits,
and logging.

## Model files are input

`.tsei` and `.pyz` files are parsed by application code. Do not load model
files from untrusted sources without reviewing the parser and testing in an
isolated environment. A malicious container could cause excessive memory use
or a denial of service.

## Secrets and signing keys

This repository does not contain an Android signing key. Do not commit `.jks`,
`.keystore`, `.p12`, `.pfx`, passwords, API tokens, or private keys. If a key is
exposed, rotate it immediately.

## Dependencies and CI

The build workflow installs a pinned numpy version and uses GitHub-hosted
runners. GitHub Actions workflows use least-privilege permissions and do not
receive secrets for builds. CodeQL and Dependabot are enabled.

## Out of scope

- Answers that are factually wrong; see the model limitations.
- Prompt-injection or content-quality issues without a security boundary.
- Vulnerabilities in third-party model providers or websites reached through
  optional web research.
- Denial of service caused by intentionally loading an untrusted model file on
  a host you control.
