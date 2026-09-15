# Releasing mcp-server-ghed

Release checks and publication use the existing GitHub repository and a PyPI
Trusted Publisher. The publishing job uses short-lived GitHub OIDC credentials;
no stored PyPI API token is required.

## One-time PyPI setup

In the package owner's PyPI account, open
[Publishing](https://pypi.org/manage/account/publishing/) and add a pending
GitHub publisher with these exact values:

| Field | Value |
|---|---|
| PyPI project | `mcp-server-ghed` |
| Repository owner | `Decilion` |
| Repository | `ghed-mcp` |
| Workflow filename | `publish.yml` |
| Environment | `pypi` |

A pending publisher creates the project on first successful publication. It does
not reserve the project name. The owner must complete account verification and
required two-factor authentication directly in PyPI.

## Versioned release

1. Update the version in pyproject.toml, ghed_mcp/__init__.py and
   ghed_mcp/client.py. Move Unreleased notes into a dated changelog entry.
2. Reinstall editable metadata, run tests, build into a fresh output directory,
   and run twine check. Inspect compatibility notes and distribution contents.
3. Commit and push; wait for CI on that exact commit to pass.
4. Create the matching tag and GitHub release. Attach exactly one wheel, one
   source archive and a SHA256SUMS file containing their SHA-256 hashes.
5. Run the Publish to PyPI workflow on main with the published tag, for example:

   ```bash
   gh workflow run publish.yml --repo Decilion/ghed-mcp -f tag=v0.6.0
   ```

The workflow verifies the tag/version, published release, file hashes, package
metadata and installed-wheel tests before uploading those same release assets to
PyPI. Publication occurs only on an explicit workflow dispatch. Set `dry_run=true`
to execute the full verification job without uploading. The `pypi` environment
allows dispatches from `main` only.

After publication, verify the PyPI version and file hashes, install from PyPI in
a fresh virtual environment, initialize the MCP server, and update README install
instructions and internal continuity records. Restart existing MCP clients.

If first-time PyPI setup is incomplete, the GitHub release remains installable
from its attached wheel. Finish account/publisher setup before dispatching the
workflow. Package uploads cannot be overwritten; investigate any partial upload
before retrying.

Reference: [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/).
