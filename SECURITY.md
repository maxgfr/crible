# Security Policy

## Deployment model — read this first

crible ships **without authentication by design** (ADR-0002): it is a
single-operator tool for a **private network**. The README says it plainly and
it bears repeating here:

> Do **not** expose port 8000 directly to the public internet. Put crible
> behind your reverse proxy / VPN, or bind it to loopback.

An exposed instance gives anyone query access to the API and its dataset —
that is a deployment mistake, not a vulnerability. The GitHub Pages demo is
static and holds no server-side state.

What *is* in scope as a vulnerability, for example:

- DSL/SQL injection past the whitelist + parametrization (NFR-011),
- path traversal or file disclosure through the API,
- the ingest pipeline executing untrusted remote content,
- secrets leaking into images, logs or published demo data.

## Supported versions

The latest release (and `main`) receive fixes. There are no backports.

## Reporting a vulnerability

Please use **GitHub private vulnerability reporting** (Security → Report a
vulnerability on the repository) rather than a public issue. Include a
reproduction if you can.

This is a solo-maintained project: acknowledgement is best-effort, typically
within a week. Fixes are released as soon as they are ready and credited to
the reporter unless you prefer otherwise.
