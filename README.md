# copilot-cli-ralph

This project runs the local loop binary inside Docker and forwards a Copilot token into the container.

Before using `make run` or `make install`, make sure:

- `jq` is installed on the host
- you are logged in to GitHub Copilot and `~/.config/github-copilot/apps.json` exists

If `COPILOT_GITHUB_TOKEN` is already set, it is used as-is.
Otherwise, the launcher and `Makefile` read the first non-empty `oauth_token` from `~/.config/github-copilot/apps.json` with `jq`.
