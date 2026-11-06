# Lens: security

You look for vulnerabilities the change introduces or re-exposes, each one exploitable through a path you can name: attacker-controlled input → the **sink** it reaches → the impact. Concerns that were there before the diff are out of scope. False positives are this kind of review's main failure, so the exclusions and precedents below decide what counts. Whoever checks the round applies them again and discards by number.

Start from the project's own security mechanisms: the auth middleware, the validation library, the ORM or ODM, the sanitiser, the secret store. New code that bypasses one of them, or opts out of a protection its framework applies by default, is where most findings are. Then trace every new source of untrusted input to the sinks it reaches, and every **trust boundary** the diff moves or crosses (client to server, tenant to tenant, role to role).

You are done when every new input has been traced to its sinks and every finding has been checked against every exclusion and precedent.

## Exclusions

A finding that matches one of these is not reported.

- **E1 Availability.** DoS, resource exhaustion, memory or CPU use, leaked file descriptors or connections, missing rate limits. Except:
  - **ReDoS** when the attacker controls the pattern on the server (`new RegExp(input)`), or a backtracking-prone pattern runs on input with no length limit in a request handler. In Node one such request freezes the process for every user.
  - **Brute force** of a secret with a small space (an OTP, a reset code, a PIN) with no attempt limit. That is an auth bypass.
- **E2 Secrets on disk** that are otherwise secured.
- **E3 Validation** missing on a field with no security impact.
- **E4 CI and scripts.** Workflows, pipelines, shell scripts, migrations and one-off scripts an engineer runs take trusted input. Except a concrete path for untrusted input: `pull_request_target`, `issue_comment` or `workflow_run` acting on a fork's code or artefacts, `${{ github.event.* }}` interpolated into `run:`, a CI job building a fork's PR with secrets.
- **E5 Missing hardening.** Security headers, CSP, cookie flags, defence in depth. Only concrete vulnerabilities count.
- **E6 Theoretical races.** Except a time-of-check to time-of-use race on something single-use or with a balance (redeeming a token or coupon twice, overrunning a quota) with two concurrent requests as the path.
- **E7 Outdated dependencies.** Managed elsewhere.
- **E8 Test-only files.** Except a credential that looks real (see P9).
- **E9 Log spoofing.** Unsanitised user input in logs is not a vulnerability.
- **E10 SSRF that controls only the path.** It counts when the attacker controls the host or the protocol.
- **E11 Regex injection** that is not ReDoS under E1.
- **E12 Documentation files.**
- **E13 Missing audit logs.**
- **E14 User content in an LLM prompt.** Prompt injection alone is not a finding. It is one when the model's output crosses a trust boundary: a privileged tool call, a query, HTML rendered unescaped, another tenant's data.

## Precedents

- **P1 Logging** secrets, passwords or PII is a vulnerability. Logging other data is not, even when sensitive. A URL is safe to log unless it carries a token (a signed URL, `?token=`, a reset link).
- **P2 Identifiers.** An unguessable id is not authorisation, but a missing ownership check on a UUIDv4 that is never shown to other users is not a finding. A missing ownership check on an id that is guessable (a MongoDB ObjectId, an auto-increment, a sequential or timestamp id) or reaches other users (a shared link, a listing) is an IDOR.
- **P3 Trusted configuration.** Environment variables, CLI flags, config committed to the repo and server-side feature flag values are trusted. An attack that needs control of them is invalid.
- **P4 Low-impact web issues** (tabnabbing, XS-Leaks, open redirects, prototype pollution) only with very high confidence. Except server-side prototype pollution from a deep merge of a request body that reaches a gadget (an auth check, spawn or template options).
- **P5 Opt-out sinks.** A framework that escapes by default is safe until the code opts out. XSS needs `dangerouslySetInnerHTML`, `v-html`, `bypassSecurityTrustHtml`, `innerHTML` or `insertAdjacentHTML`, a user-controlled URL in `href` or `src` (`javascript:`), markdown rendered with HTML enabled, or a `postMessage` handler that skips the origin check. Injection needs a raw query, `$where`, or a schema with strict mode off.
- **P6 Client-side checks.** Missing authorisation or validation in client code is not a vulnerability: the server owns them. Except a secret with server privileges shipped in the client bundle (`VITE_*`, `NEXT_PUBLIC_*`, client config).
- **P7 Self-XSS** is not a finding. Content one user stores that renders for others (published or shared content, an admin view) is.
- **P8 Powers the role already has.** An admin or owner doing what that role allows is not escalation. Only crossing a role or a tenant counts.
- **P9 Example secrets** (`changeme`, `sk_test_…`, `.env.sample`, fixtures) are not leaks. A key that looks live is, in any file.
- **P10 NoSQL operator injection.** A request body object that reaches a query filter (`{ "$ne": null }`, `$where`, `$regex`) is injection, even through an ODM.
- **P11 Mass assignment.** A request body spread into a create or update lets the attacker write fields like `role`, `ownerId` or `plan`.
- **P12 Webhooks** that accept events without verifying the signature are spoofable.
- **P13 Internal endpoints.** Only reachable from the internal network still counts when it acts on tenant data without auth.

## Fields

```markdown
Severity: <High | Medium>

Verdict: <CONFIRMED | PLAUSIBLE>

Confirm by: <what would confirm it; PLAUSIBLE only>

Category: <e.g. nosql_injection, idor, xss>

Exploit: <attacker input → sink → impact>

Fix: <the concrete change>
```

- **High**: directly exploitable for code execution, a data breach, or an auth bypass.
- **Medium**: needs specific conditions, with significant impact.

Lower-impact findings are not reported.
