# TODO

## Security Follow-ups

- [ ] Close remaining filesystem time-of-check/time-of-use windows.
  - Current filesystem-link validation happens before `shutil.copytree`, so a concurrently modified source tree could theoretically change between validation and copying.
  - Overwrite now moves the marked target to a same-parent backup path and revalidates that backup before deleting it, but a concurrently writable output parent can still create narrow races around backup cleanup and partial-output cleanup.
  - For a hardened implementation, copy into a temporary staging directory, validate the staged tree for filesystem links and unexpected files, then atomically move or rewrite from the validated staging directory.
  - Keep this as a future hardening item unless the engine starts processing untrusted or concurrently writable source trees.

- [ ] Add CI coverage for filesystem-link rejection on platforms with link creation privileges.
  - Run the symlink tests on Linux or macOS by default because symlink creation is normally available there.
  - Run the Windows junction tests on Windows because junction creation can be available even when symlink creation is not.
  - Add a Windows CI job once symlink creation is confirmed, either through Developer Mode, an elevated runner, or a self-hosted runner with `SeCreateSymbolicLinkPrivilege`.
  - Keep the local Windows test skip so developer machines without symlink rights can still run the suite.

- [ ] Add dependency vulnerability auditing to verification.
  - Keep `pip-audit` as a development/CI tool, not a runtime dependency of generated packages.
  - Run `python -m pip_audit` in CI after installing test dependencies.
  - Expect the local editable package to be skipped because it is not published on PyPI.

## Option 3: General-purpose Package Transformation Engine

Build toward a reusable package transformation engine that can instantiate independent Python packages from a source package while preserving correctness across Python code, packaging metadata, documentation, tests, and future extension points.

This is a larger direction than the current minimal package instantiation engine. The best path is incremental: first make the existing transformation model explicit, then replace fragile text edits with structured file-specific transforms, then generalize the system into a configurable engine.

### Suggested Path

- [ ] Stabilize the current generator as the baseline.
  - Keep the existing `base-pattern-engine` behavior passing before expanding scope.
  - Treat the current package as the first fixture for the general engine.
  - Preserve the requirement that generated packages are standalone and do not keep generator powers.

- [ ] Define a transformation manifest.
  - Describe source package identity, target package identity, files to copy, files to exclude, generated-package strip rules, exposed runtime API, and metadata rewrite rules.
  - Keep the first manifest local and simple, then decide later whether it should live in TOML, YAML, or Python.
  - Use the manifest as the contract between the CLI and transformation engine.

- [ ] Introduce a transformation pipeline.
  - Split the engine into stages: discover source, plan output, copy files, classify files, transform files, strip generator-only pieces, validate output.
  - Return a structured result that includes generated path, transformed files, skipped files, warnings, and validation status.
  - Keep the CLI thin and move transformation decisions into testable engine components.

- [ ] Add file classification.
  - Classify files by role: Python source, TOML metadata, Markdown docs, license text, binary/unknown, package data, tests.
  - Route each file type through the appropriate transformer.
  - Make unknown text files opt-in or warning-only rather than blindly rewriting everything.

- [ ] Replace Python string replacement with semantic Python rewriting.
  - Prefer `LibCST` for Python transforms because it preserves comments and formatting better than built-in `ast` plus `ast.unparse()`.
  - Rewrite imports, module references, selected constants, and known public symbols through syntax-aware transforms.
  - Keep a small fallback for intentionally literal strings such as `MODULE_NAME` and `DISTRIBUTION_NAME`, where changing the string value is desired.

- [x] Replace line-based TOML edits with TOML-aware edits.
  - Use `tomlkit` so `pyproject.toml` can be updated while preserving formatting and comments.
  - Rewrite project name, description, script entries, package-data settings, and package discovery settings structurally.
  - Remove generated-package-only or source-package-only sections by key, not by line scanning.

- [ ] Keep documentation placeholder-based.
  - Use explicit placeholders for generated README content instead of semantic prose rewriting.
  - Validate that generated docs contain no unresolved placeholders and no source package identity leaks.
  - Keep root source docs separate from generated package docs.

- [ ] Add validation after generation.
  - Confirm generated package imports without the source engine installed.
  - Confirm generated package metadata has the target distribution name.
  - Confirm no generator-only modules, CLI scripts, or `_self` bundle remain.
  - [x] Confirm no unresolved package-template placeholders remain in generated text files.
  - Confirm no source identity leaks remain in generated Python, TOML, or docs except where explicitly allowed.

- [ ] Expand tests around transformation safety.
  - Add fixtures with comments, strings, imports, aliases, relative imports, and nested packages.
  - Verify Python transforms do not rewrite unrelated prose strings unless configured.
  - Verify TOML transforms preserve unrelated sections.
  - Add end-to-end tests that uninstall the source engine, install the generated package, and exercise its public API.

- [ ] Design the general CLI experience.
  - Keep the current simple path: `base-pattern-engine instantiate --name my_package --license MIT --overwrite`.
  - Add optional advanced inputs later, such as `--manifest`, `--source-package`, or `--dry-run`.
  - Consider a `plan` command that previews files to copy, transform, strip, and validate before writing output.

- [ ] Add observability and dry-run support.
  - Report transformed files, skipped files, stripped files, warnings, and validation failures.
  - Add a dry-run mode that produces the transformation plan without writing files.
  - Keep output concise by default, with a verbose mode for debugging.

- [ ] Continue dependency policy decisions as structured rewriting expands.
  - `tomlkit` is now a generator dependency for TOML-aware pyproject transforms.
  - Add `LibCST` only when semantic Python rewriting begins.
  - Keep generated packages free of generator dependencies.
  - Separate generator dependencies from generated package runtime dependencies.

- [ ] Document the engine model.
  - Explain the difference between source engine, transformation manifest, generated package, and generated package runtime API.
  - Document which transformations are semantic, which are placeholder-based, and which are intentionally unsupported.
  - Keep examples focused on the client workflow: install from a pinned Git tag or commit, instantiate, upgrade, reinstantiate, uninstall engine.

### First Practical Milestone

- [x] Refactor the current `instantiate()` flow into small internal stages without changing behavior.
- [ ] Add a tiny in-code transformation manifest for the current package.
- [x] Replace generated `pyproject.toml` edits with `tomlkit`.
- [ ] Add validation that reports source identity leaks by file type.
- [ ] Keep Python rewriting as string-based for one more milestone, then switch to `LibCST` once the pipeline is stable.
