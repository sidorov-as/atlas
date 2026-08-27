"""Atlas distribution composer.

Resolves a deployment manifest to a lock file recording exact plugin
versions and integrity hashes (`docs/plugin-architecture.md:493-547`). The
same CLI is invoked by CI building the default distribution and by a
hypothetical external operator building their own.

Lock -> `INSTALLED_APPS` / frontend module generation and the full
composition-validation rule set are later tasks (3.1-3.3); this package
currently only covers manifest parsing (`manifest.py`), the lock schema
(`lock.py`), and manifest -> lock resolution (`resolver.py`).
"""
