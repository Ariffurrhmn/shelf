# Security

The repository and the deployed site are both public. Anything committed here can be read by anyone, so the rules below exist to keep mistakes from becoming leaks.

## Drafts

Set `draft: true` in an artifact's metadata to exclude it from the build and from the public site. A draft is only hidden from the site: it is still committed to the repository, which is public. Do not commit anything that must stay private, even as a draft.

## Secret and personal-data scanning

The validator is planned to scan every artifact for secrets (API keys, tokens, passwords) and personal data, and to fail the build when it finds something suspicious. It is not implemented yet, so until it exists, review artifacts by hand before committing. The patterns it will look for are TBD.

## Sandboxed embeds

Artifacts embedded in my portfolio site should go in an iframe with the `sandbox` attribute, so a buggy or misbehaving artifact cannot affect the host page. Which sandbox permissions to allow is TBD and may depend on the artifact (for example, `storage: local` artifacts need different treatment).

## Ephemeral by default

Artifacts store nothing and send nothing to a server unless their metadata says otherwise (`storage: local`, or domains listed in `network`). See [../spec/SPEC.md](../spec/SPEC.md).
