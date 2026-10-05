"""Optional hooks on a plugin's entry-point module, called by core's
runtime entry-point-loading phase.

`register_runtime()` runs once per active plugin in manifest order, so at
that point a plugin cannot assume that registrations made by *other*
plugins (search sources, search engines, ...) already exist. A plugin that
must look at the complete set of registrations, and fail startup when they
are unusable, exposes a module-level `finalize_runtime()` hook instead.
Core calls it for every active plugin after every `register_runtime()` has
run and before composition validation, so an exception stops the process
before it accepts traffic. A disabled plugin's hook is never called.
"""

RUNTIME_FINALIZATION_HOOK = "finalize_runtime"
"""Name of the optional hook on a plugin's entry-point module."""
