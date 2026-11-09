# Capability: packaging-surface

Baseline: jasonacox/tinytuya v1.20.0 @ 8512d8364a9d0e351bbec2597bafa17595545b13 (2026-07-06).

## Summary

This capability is the package-facing contract of TinyTuya: what `import tinytuya` exposes (top-level re-exports assembled from the `tinytuya/core` subpackage and the legacy shadow module `tinytuya/core/core.py`), how the single version string is declared and consumed at build time, how install metadata (`setup.py`, `pyproject.toml`, `requirements.txt`) handles the crypto-backend and optional dependencies, which config file names are constants of the package, and the small public error surface (`DecodeError`, numeric error codes via `error_json()`). Protocol/crypto *internals* (framing, AES modes, session negotiation) are owned by protocol-crypto; only the package-level selection and surfacing of a crypto backend is covered here.

## Primary code locations
- `tinytuya/__init__.py` — top-level namespace: docstring API catalog + `from .core import *` + named device/Cloud/Monitor exports.
- `tinytuya/core/__init__.py` — aggregator re-exporting all core submodules plus the shadow module `.core`.
- `tinytuya/core/core.py` — legacy shadow module holding `version`/`__version__`/`__author__`, `set_debug()`, misc helpers.
- `tinytuya/core/const.py` — network/tuning constants and the four config-file name constants.
- `tinytuya/core/error_helper.py` — numeric error-code namespace (900–914) and `error_json()`.
- `tinytuya/core/exceptions.py` — `DecodeError` exception type.
- `tinytuya/core/crypto_helper.py` — runtime crypto-backend auto-detection at import time.
- `setup.py` / `pyproject.toml` / `requirements.txt` — install and build metadata.
- `tinytuya/__main__.py` — console-script/module entry point (`dummy()` + module-level CLI).
- `tinytuya/core/XenonDevice.py` — `load_devicefile()`/`device_info()` devices.json loaders.
- `README.md` § TinyTuya Installation; `RELEASE.md` — install claims and per-release packaging notes.

## Requirements

### Requirement: Single top-level public namespace
The package SHALL expose its whole user API from the top-level `tinytuya` namespace: `OutletDevice`, `CoverDevice`, `BulbDevice` and `Cloud` are imported by name, and every public name of the `tinytuya.core` subpackage is re-exported via star-import, so `import tinytuya; tinytuya.OutletDevice(...)` and `from tinytuya import <anything public>` work without touching submodules.
- Status: VERIFIED
- Evidence: doc: `tinytuya/__init__.py` module docstring is itself the exported-API catalog (classes, Device methods, Cloud methods); commit `b46865c1ce08` "clean up new imports in core.py"
- Anchor: `tinytuya/__init__.py:92-100`

### Requirement: No `__all__` gating on star re-exports
The package SHALL NOT define `__all__` in any module; the public surface is therefore "every public name" of each star-imported core submodule, which keeps legacy helpers (e.g. `version`, `SCANTIME`, `DEVICEFILE`, `error_json`) importable from the top level as a compatibility contract.
- Status: VERIFIED
- Evidence: `grep -rn "__all__" tinytuya/` returns zero hits at pin; `tinytuya/__main__.py:27` consumes this surface directly (`from . import wizard, scanner, version, SCANTIME, DEVICEFILE, SNAPSHOTFILE, CONFIGFILE, RAWFILE, set_debug`); commit `be63f9b4fe79` "fix import", commit `b90172457960` "fix import of scanner, fix pylint"
- Anchor: `tinytuya/core/__init__.py:5-14`; `tinytuya/__main__.py:27`

### Requirement: Core aggregator with shadow-module re-export
`tinytuya/core/__init__.py` SHALL aggregate exactly these submodules by star-import — `crypto_helper`, `message_helper`, `exceptions`, `error_helper`, `const`, `XenonDevice`, `udp_helper`, `Device`, `command_types`, `header` — and additionally re-export the legacy shadow module `.core` (including `__version__`/`__author__`), preserving the pre-split `tinytuya/core/core.py` namespace as an import compatibility layer.
- Status: VERIFIED
- Evidence: commit `b46865c1ce08` "clean up new imports in core.py"; commit `be63f9b4fe79` "fix import"; history shows core.py was split into the submodule set while keeping `from .core import *` chains intact
- Anchor: `tinytuya/core/__init__.py:5-18`

### Requirement: Single-source version declaration
The package SHALL declare its version in exactly one place — `version_tuple = (1, 20, 0)` rendered into `version = __version__ = "1.20.0"` with `__author__ = "jasonacox"` — and every consumer (package exports, setup.py metadata, CLI description) SHALL read that value rather than duplicating a literal.
- Status: VERIFIED
- Evidence: doc: `RELEASE.md` release-note headers vs. bumps; commit `cd99020e4fa4` "Bump version number", commit `7ca1b531ee8a` "Bump version to 1.17.4 and add Release notes", commit `d3bdd7078583` "release: bump version to 1.19.0"
- Anchor: `tinytuya/core/core.py:104-106`; propagated via `tinytuya/core/__init__.py:17-18` and `tinytuya/__init__.py:93-94`

### Requirement: Build-time version import drives setup metadata
`setup.py` SHALL derive the distribution version by importing the package (`from tinytuya import __version__`) rather than parsing files; consequently the build environment MUST be able to import tinytuya — which transitively requires a crypto backend — so the PEP-517 `[build-system] requires` list SHALL include setuptools plus `colorama`, `requests` and `cryptography`.
- Status: VERIFIED
- Evidence: commit `8ab0d0df4d31` "fix: update import handling for package version retrieval in setup.py"; commit `5f3fe554a1d0` "Add pyca/cryptography to setup.py and some minor docu updates"
- Anchor: `setup.py:10` (import), `setup.py:41` (`version=__version__`); `pyproject.toml:1-2`

### Requirement: Runtime crypto-backend auto-selection with hard failure
At import time the package SHALL probe crypto backends in priority order pyca/cryptography (skipping versions ≤ 3.0, which need a `backend=` parameter) → PyCryptodomex → PyCrypto (re-labelled PyCryptodome when `Crypto.version_info[0] >= 3`) → pyaes, adopt the first that imports, and SHALL raise `ModuleNotFoundError` naming the installable options if none is found.
- Status: VERIFIED
- Evidence: doc: README.md:49-53 (four supported crypto libraries); commit `18474664bc13` "Remove crypto import", commit `5f3fe554a1d0` "Add pyca/cryptography to setup.py…"
- Anchor: `tinytuya/core/crypto_helper.py:9-39` (priority loop :9, ≤3.0 skip :14-16, PyCrypto→PyCryptodome relabel :29, raise :38-39)

### Requirement: Install metadata adds exactly one crypto dependency
`setup.py` SHALL install base dependencies `requests` and `colorama`, then probe distributions in order `cryptography` → `pycryptodome` → `pyaes` → `pycrypto` and append only the first already-installed one (defaulting to `cryptography` when none is present) to `install_requires` — so pip never force-installs a redundant crypto stack.
- Status: VERIFIED
- Evidence: doc: README.md:43 "Pip will attempt to install `cryptography`, `requests` and `colorama` if not already installed"; commit `5f3fe554a1d0` "Add pyca/cryptography to setup.py…"
- Anchor: `setup.py:15-26` (base deps :15-19, candidate list :21-26), `setup.py:28-37` (probe + append)

### Requirement: Requirements floor consistent with crypto probe
The pinned requirements file SHALL set `cryptography>=3.1`, consistent with the runtime probe's rejection of cryptography ≤ 3.0, and document that the crypto dependency is substitutable; `requests` and `colorama` are listed unpinned, and `netifaces` is shipped commented-out as an optional discovery aid.
- Status: VERIFIED
- Evidence: doc: README.md:47-59 "Alternate Install on Space- or Dependency-Limited Systems"; runtime skip at `tinytuya/core/crypto_helper.py:14-16`
- Anchor: `requirements.txt:2`; `tinytuya/core/crypto_helper.py:14-16`

### Requirement: Console entry point executes CLI at module import
The distribution SHALL register console script `tinytuya` pointing at `tinytuya.__main__:dummy`, where `dummy()` is intentionally a no-op — the CLI's argparse setup and dispatch run as module-level code at import — and help output SHALL adapt its program name between `python3 -m tinytuya` and the installed console script by inspecting `sys.argv[0]`.
- Status: VERIFIED
- Evidence: doc: README.md:39-40 ("Optional: Install Command Line Tool — `pipx install tinytuya`"); commit `6b92610afad7` "Add version switch to CLI"
- Anchor: `setup.py:50` (entry_points); `tinytuya/__main__.py:268-270` (`def dummy(): pass`), `tinytuya/__main__.py:30` (prog sniffing)

### Requirement: `version` subcommand reports installed version
The CLI SHALL provide a `version` subcommand printing the installed library version sourced from the single-source `version` constant, and SHALL skip scanner/wizard device-file initialization for it (as for `list` and `help`).
- Status: VERIFIED
- Evidence: doc: RELEASE.md:54 "CLI: New `version` subcommand — `tinytuya version` prints the installed TinyTuya version" (v1.18.0); commit `6b92610afad7` "Add version switch to CLI"
- Anchor: `tinytuya/__main__.py:256-257` (dispatch/print), `tinytuya/__main__.py:215` (file-setup skip)

### Requirement: Numeric error-code namespace and error_json contract
The package SHALL export a stable numeric error-code namespace `ERR_JSON`=900 through `ERR_KEY_OR_VER`=914 with a human-readable string per code (including a `None` → "Unknown Error" entry), and `error_json(number, payload)` SHALL always return a dict shaped `{"Error": <message>, "Err": <code-as-string>, "Payload": <payload>}`, falling back to "Unknown Error" for unrecognized codes instead of raising.
- Status: VERIFIED
- Evidence: doc: RELEASE.md:24 (v1.20.0 "timeout errors report `ERR_TIMEOUT`… `error_json()` handles unknown codes"); the fallback is `error_codes.get(number, error_codes[None])`
- Anchor: `tinytuya/core/error_helper.py:10-24` (codes), `:26-43` (message map), `:46-51` (`error_json()`)

### Requirement: DecodeError exported for frame-level failures
The package SHALL define and export a single library exception type `DecodeError(Exception)` through the core star-import chain, as the signal for undecodable/corrupt frames (e.g. headers claiming oversize payloads), distinct from the dict-shaped device error contract.
- Status: VERIFIED
- Evidence: doc: RELEASE.md:24 (v1.20.0 "truncated frames raise `DecodeError`"); raised at `tinytuya/core/message_helper.py:97` against `MAX_PAYLOAD_LENGTH`
- Anchor: `tinytuya/core/exceptions.py:4-5`; re-exported via `tinytuya/core/__init__.py:7`

### Requirement: Config-file names as package constants with override points
The package SHALL define its configuration surface as overridable constants `CONFIGFILE='tinytuya.json'`, `DEVICEFILE='devices.json'`, `RAWFILE='tuya-raw.json'`, `SNAPSHOTFILE='snapshot.json'`, and SHALL allow per-invocation override: `Cloud(..., configFile=CONFIGFILE)` for credentials, CLI flags `-device-file`/`-snapshot-file`/`-raw-response-file`/`-credentials-file`, and wizard module-level rebinding.
- Status: VERIFIED
- Evidence: doc: README.md:619-628 (CLI file flags with those defaults), README.md:115-116 (wizard writes devices.json / tuya-raw.json / snapshot.json); commit `736ba6774d88` "Update release notes for version 1.17.4 to include Cloud configFile option"
- Anchor: `tinytuya/core/const.py:21-27`; `tinytuya/Cloud.py:50` (default arg), `:89`, `:107` (open); `tinytuya/wizard.py:52`; `tinytuya/__main__.py:102`, `:249`

### Requirement: Centralized dual-format devices.json loader
The library SHALL provide one public loader, `load_devicefile(fname=None)` defaulting to `DEVICEFILE`, that accepts both the flat `[{...}]` list and the `{"devices": [{...}]}` wrapped-dict format, coerces any other shape to an empty list, and returns `[]` on any failure instead of raising; library, CLI, scanner, wizard and server paths SHALL all consume it, and `device_info(dev_id)` SHALL resolve a single device through it.
- Status: VERIFIED
- Evidence: doc: RELEASE.md:42 (v1.18.0 "All loading paths… now support both formats via a new centralized `load_devicefile()` helper"); commit `3cea89363d21` "feat: update version to 1.18.0, enhance device file loading, and improve error handling in CLI"; consumers at `tinytuya/cli.py:32`, `tinytuya/cli.py:86`, `tinytuya/wizard.py:119`, `tinytuya/scanner.py:1184`
- Anchor: `tinytuya/core/XenonDevice.py:65-89` (loader), `:91-108` (`device_info()`)

### Requirement: No declared interpreter floor despite Python-3-only support
Packaging metadata SHALL gate installs on a minimum Python version — as of this pin it does not: neither `setup.py` nor `pyproject.toml` sets `python_requires` — while official Python 2.7 support was removed in v1.13.0 and dormant Python-2 compatibility shims (`from __future__` imports, `IS_PY2` branches, `raw_input` aliasing) remain in `tinytuya/core/core.py`/`tinytuya/core/crypto_helper.py`; classifiers declare "Programming Language :: Python :: 3" only.
- Status: VERIFIED
- Evidence: doc: RELEASE.md:233 (v1.13.0 notes: "Officially removes Python 2.7 support."); commit `b044a775492a` "Remove Python 2.7 support", commit `5591ec72fdc7` "Remove python 2.7 in doc", commit `bf24e363e0da` "Remove Python 3.6 build test as it's not available on 22.04"
- Anchor: absence in `setup.py:39-56` and `pyproject.toml:1-2`; shims at `tinytuya/core/core.py:79`, `:94-97`, `:112`; `tinytuya/core/crypto_helper.py:4`

## Known gaps / open questions
- **Crypto priority mismatch (setup vs runtime).** `setup.py:21-26` probes `cryptography → pycryptodome → pyaes → pycrypto`, while `tinytuya/core/crypto_helper.py:9` prefers `pyca/cryptography → PyCryptodomex → PyCrypto → pyaes` — the pyaes/pycrypto positions are swapped, and setup probes the `pycryptodome` distribution (imports as `Crypto`) whereas runtime names the branch `PyCryptodomex` (`Cryptodome` namespace). Both work (the PyCrypto branch re-labels v3+ as PyCryptodome at `tinytuya/core/crypto_helper.py:29`), but install-time preference and run-time preference are not the same policy.
- **pyproject.toml is build-backend config only.** `pyproject.toml:1-2` contains just `[build-system] requires`; all distribution metadata still lives in legacy `setup.py`. No `[project]` table, no `requires-python`, no optional-dependency groups — the README's documented `--no-deps` workflow (README.md:59) has no metadata equivalent (e.g. extras).
- **colorama is runtime-optional but install-required.** `tinytuya/core/core.py:83-89` degrades gracefully without colorama (v1.17.3, commit `78505b78c164`; RELEASE.md:105), yet `setup.py:17` keeps it in `INSTALL_REQUIRES` and `pyproject.toml:2` in build requires — mildly at odds with README.md:55 framing it as optional.
- **Deprecated import mechanics still shipped.** `setup.py:2-8` falls back to deprecated `pkg_resources.get_distribution` when `importlib.metadata` is unavailable; `tinytuya/core/core.py` is a shadow module re-exported wholesale (`tinytuya/core/__init__.py:16`), so `crypto_helper`/colorama machinery is imported through two paths — the exact mechanics of a future core.py removal are unspecified anywhere in docs.
- **No declared Python floor.** Support policy ("Python 3", README install flow, CI matrix per commits `bf24e363e0da`/`192ffdcf6e86`) is nowhere encoded in metadata (`python_requires` absent); the concrete supported-version list is unknown at pin.
- **Error-code numbers are an undocumented-by-API contract.** `API.md` describes the `{'Error','Err'}` dict shape, but the numeric range 900–914 has no "stability" statement; adding codes is silently breaking-adjacent for code that string-matches `Err`. Not resolved by any doc found in `recon/evidence/docs/`.
- **Entry-point-by-side-effect fragility.** The console script works only because importing `tinytuya.__main__` executes the CLI at module level (`tinytuya/__main__.py:30-33` argparse build runs on import); any future move of dispatch into a function without updating `setup.py:50` would ship a no-op `tinytuya` command. No test asserting console-script behavior was located in `recon/evidence/tests_inventory.txt`.
- **`netifaces` policy drift.** Commented out in `setup.py:18` and `requirements.txt`, yet README.md and scanner docs mention it as needed on multi-interface machines; whether it is a soft extra or a manual step is not formalized.
- **PR provenance thin.** Only 4 of 946 mined commits carry PR refs; packaging-history intent here is provenanced by commit subjects from `recon/evidence/bundle_packaging-surface.txt` (verified shas at pin), not by issue/PR discussion.
