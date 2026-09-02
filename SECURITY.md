# Security policy

## Reporting a vulnerability

Do not disclose exploitable vulnerabilities in a public issue. Until a project security contact is configured, open a GitHub Security Advisory in the repository. Replace this paragraph with the final private reporting channel before the first public release.

## Sensitive data

Never include a real receipt, unmasked CBU/CVU, CUIT/CUIL, account holder name, operation number or bank access information in an issue, pull request, test fixture or log excerpt.

## MVP threat priorities

- Malformed image parsers and decompression bombs.
- Oversized requests and resource exhaustion.
- Command injection through subprocess-based analyzers.
- Temporary-file disclosure or failed cleanup.
- Sensitive OCR output in logs or traces.
- Unrestricted CORS and public API abuse.
- Dependency/model supply-chain integrity.

The implementation security design belongs in feature SDD/TDD documents and must include hostile-input tests.
