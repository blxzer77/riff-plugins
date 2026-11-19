#!/usr/bin/env bash
# Installs a released `riff` binary on Linux or macOS.
#
#   install.sh [version or tag]     e.g. install.sh 0.1.0, install.sh riff-v0.1.0
#
# RIFF_INSTALL_DIR (default ~/.local/bin), RIFF_VERSION and RIFF_REPO
# (default blxzer77/riff-plugins) override the defaults. The archive is checked
# against the release's SHA256SUMS before anything is installed.
set -euo pipefail

repo="${RIFF_REPO:-blxzer77/riff-plugins}"
install_dir="${RIFF_INSTALL_DIR:-$HOME/.local/bin}"
requested_version="${1:-${RIFF_VERSION:-}}"

if [ "$#" -gt 1 ]; then
  printf 'usage: install.sh [version or tag]\n' >&2
  exit 2
fi

case "$(uname -s)" in
  Linux) asset_os=linux ;;
  Darwin) asset_os=macos ;;
  *)
    printf 'install.sh supports Linux and macOS; use install.ps1 on Windows.\n' >&2
    exit 1
    ;;
esac

case "$(uname -m)" in
  x86_64|amd64) asset_arch=x86_64 ;;
  aarch64|arm64) asset_arch=aarch64 ;;
  *)
    printf 'unsupported architecture: %s\n' "$(uname -m)" >&2
    exit 1
    ;;
esac

fetch() {
  curl --fail --silent --show-error --location "$@"
}

if [ -z "$requested_version" ]; then
  # The repository also tags its skills (plain vX.Y.Z), so the newest release
  # overall is not necessarily a riff release: take the newest riff-v one that
  # is not a pre-release.
  releases="$(fetch --header 'Accept: application/vnd.github+json' "https://api.github.com/repos/$repo/releases?per_page=100")"
  requested_version="$(printf '%s\n' "$releases" | awk -F'"' '
    /"tag_name"/ && !found {
      for (i = 1; i <= NF; i++) {
        if ($i ~ /^riff-v[0-9]+\.[0-9]+\.[0-9]+$/) { print $i; found = 1; break }
      }
    }')"
  if [ -z "$requested_version" ]; then
    printf 'no riff release found in %s; pass a version, for example: install.sh 0.1.0\n' "$repo" >&2
    exit 1
  fi
fi

case "$requested_version" in
  riff-v*) tag="$requested_version" ;;
  *) tag="riff-v$requested_version" ;;
esac
if [[ ! "$tag" =~ ^riff-v[0-9]+\.[0-9]+\.[0-9]+(-(alpha|beta|rc)\.[0-9]+)?$ ]]; then
  printf 'invalid riff release tag: %s\n' "$tag" >&2
  exit 2
fi

version="${tag#riff-v}"
asset="$tag-$asset_os-$asset_arch.tar.gz"
base_url="https://github.com/$repo/releases/download/$tag"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

archive="$tmp_dir/$asset"
sums="$tmp_dir/SHA256SUMS"
fetch --output "$archive" "$base_url/$asset"
fetch --output "$sums" "$base_url/SHA256SUMS"

expected="$(awk -v asset="$asset" '$2 == asset { print $1; exit }' "$sums")"
if [[ ! "$expected" =~ ^[[:xdigit:]]{64}$ ]]; then
  printf 'SHA256SUMS has no valid entry for %s\n' "$asset" >&2
  exit 1
fi
if command -v sha256sum >/dev/null 2>&1; then
  actual="$(sha256sum "$archive" | awk '{ print $1 }')"
else
  actual="$(shasum -a 256 "$archive" | awk '{ print $1 }')"
fi
if [ "$actual" != "$expected" ]; then
  printf 'SHA256 mismatch for %s: expected %s, got %s\n' "$asset" "$expected" "$actual" >&2
  exit 1
fi

mkdir -p "$tmp_dir/unpacked" "$install_dir"
tar -xzf "$archive" -C "$tmp_dir/unpacked"
install -m 0755 "$tmp_dir/unpacked/riff" "$install_dir/riff"
printf 'Installed riff %s to %s/riff\n' "$version" "$install_dir"
if [[ ":$PATH:" != *":$install_dir:"* ]]; then
  printf 'Add %s to PATH if it is not already present.\n' "$install_dir"
fi
printf 'Next: riff init, then riff web doctor.\n'
