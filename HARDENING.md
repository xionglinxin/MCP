# Offline hardening and verification

## Compatibility changes

- Both servers use the tested `mcp==1.29.0`. HTTP host/port are set on
  `mcp.settings`; `run()` receives only the transport. The listener remains
  loopback-only (`127.0.0.1`). Use a separate virtual environment per server:
  their legacy flat module names (`config`, `schema`, `server`) overlap.
- eNSP device IDs now allow 1–64 ASCII letters/digits, underscores, hyphens or
  Chinese characters. Windows reserved device names are rejected. Update older
  inputs containing separators, punctuation or longer IDs before generating.
- eNSP publishes each complete artifact set under
  `outputs/{output_name}_{timestamp}_{uuid}/`, containing `{output_name}.topo`
  and `{output_name}_{device_id}_config.txt`. Always consume returned paths;
  scripts relying on the former flat naming convention must be updated.
  `outputs://list` includes legacy files and completed bundles, hiding staging
  directories. Same-filesystem directory rename publishes the bundle; ordinary
  write/rename failures clean staging. A process crash can leave a hidden staging
  directory; this is not a durable database transaction or a cleanup service.
- Visio uses resolved path ancestry for stencil, draw, export, edit, list and
  recycle/fallback paths, including preset generators. File types are checked.
  Delete accepts only a plain filename; PowerShell single quotes are escaped.
  Fallback trash filenames are unique. Existing symlink escapes are rejected.
  These checks are not a sandbox against another local process replacing paths
  after validation. Keep the output/stencil directories trusted and private.

## Run offline tests

From the repository root, in a disposable virtual environment:

```sh
python -m pip install 'mcp==1.29.0' 'pydantic>=2' 'pytest>=7' 'setuptools>=61' 'tomli; python_version < "3.11"'
python -m pytest -q tests
python -m pip wheel --no-deps --no-build-isolation --wheel-dir dist ./ensp-mcp ./visio-draw-mcp
```

Tests exercise real schema validation and SDK entrypoint argument binding, plus
filesystem fixtures and injected write failures. COM imports are doubles;
workers, PowerShell, network listeners and real network devices are never run.
Use `MCP_SOURCE_ROOT=/path/to/older/checkout` to run the same tests against an
older source tree. Symlink tests require a platform/account permitted to create
symlinks (Linux recommended for the offline suite).

Verified on Python 3.12 with MCP 1.29.0: 32 tests passed. The same tests against
commit `5a0d9bc42a8b7c1d29fd590f83424f7dccc3f681` produced 28 failures and 4
passes. Both wheels built with no dependency installation. One SDK/Pydantic
settings forward-reference warning was emitted; tests still passed.

Wheel building validates metadata and Python module discovery, not Visio runtime
installation. Continue using the documented source checkout/editable install
workflow for templates, examples and vendor stencils; standalone wheel resource
packaging is outside this patch. Windows requires pywin32 and Microsoft Visio.

## Remaining Windows verification / release blocker

The shared Visio COM application still crosses worker-thread/apartment boundaries.
A timeout does not stop its worker; current reset/retry behavior is not a safe
hang-recovery mechanism. Do not treat this patch as production concurrency or
COM reliability certification. Avoid concurrent operations and automated retry
following a timeout; recover under operator control. A complete fix needs a
single COM-owner worker plus a process recovery boundary and Windows tests.

Before a release, use a disposable Windows/Visio setup to verify sequential draw,
export, edit, stencil cache, shutdown, concurrent-request serialization, timeout
and recovery behavior. Verify real eNSP imports and configuration application
separately. These integrations were not run in the Linux offline checks.
Vendor stencil redistribution rights and repository licensing remain unresolved;
this patch makes no licensing claim.
