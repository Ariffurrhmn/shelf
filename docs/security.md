# Security

The repository and the deployed site are both public. Anything committed here can be read by anyone, so the rules below exist to keep mistakes from becoming leaks.

## Drafts

Set `draft: true` in an artifact's metadata to exclude it from the build and from the public site. A draft is only hidden from the site: it is still committed to the repository, which is public. Do not commit anything that must stay private, even as a draft.

## Secret and personal-data scanning

The validator scans every text file in each artifact folder and fails the build when it finds:

- cloud and API credentials: AWS keys, GitHub tokens, Anthropic and OpenAI-style keys, Stripe live keys, Slack tokens, Google API keys, private key blocks, JSON web tokens;
- hard-coded assignments such as `apiKey = "..."` or `password: "..."`;
- email addresses, except `example.com`, `example.org`, `example.net`, reserved test domains and `noreply@` addresses.

Phone-number-like text produces a warning. The scan is a safety net based on patterns, not a guarantee, so still read an artifact before committing it. Secrets and email addresses are errors even in drafts.

## Sandboxed embeds

Artifacts embedded in my portfolio site should go in an iframe with the `sandbox` attribute, so a buggy or misbehaving artifact cannot affect the host page. A reasonable starting point is `sandbox="allow-scripts"`, adding `allow-same-origin` only for `storage: local` artifacts and `allow-fullscreen` (with `allow="fullscreen"`) for presentations. Revisit when the portfolio embed is built.

## Ephemeral by default

Artifacts store nothing and send nothing to a server unless their metadata says otherwise (`storage: local`, or domains listed in `network`). See [../spec/SPEC.md](../spec/SPEC.md).
