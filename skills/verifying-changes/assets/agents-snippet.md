## Verification

- Before saying a change works, run it the way it really runs (the command, the
  endpoint, the caller) and read the output. Tests and type checks are not enough.
- Look for every place that decides the behavior (config files, env vars, duplicated
  constants, middleware) before trusting one definition.
- Exercise the edges the request implies, including the old behavior that must
  remain and the failures that must not be swallowed.
- Report the commands and outputs that show it works, and list what was not verified.
