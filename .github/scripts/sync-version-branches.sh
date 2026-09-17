#!/usr/bin/env bash
set -euo pipefail

UPSTREAM_URL="${UPSTREAM_URL:-https://github.com/jumpserver/lina.git}"
DRY_RUN="${DRY_RUN:-true}"
# Complete releases, including the historical v3.10.0-7-lts branch.
version_pattern='^v[0-9]+\.[0-9]+\.[0-9]+(-[0-9]+)?(-lts)?$'

if [[ "$DRY_RUN" != true && "$DRY_RUN" != false ]]; then
  echo 'DRY_RUN must be true or false.' >&2
  exit 1
fi
if [[ "$(git rev-parse --is-shallow-repository)" == true ]]; then
  echo 'Full Git history is required; use actions/checkout with fetch-depth: 0.' >&2
  exit 1
fi

report() {
  printf '%s\n' "$1"
  if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
    printf '%s\n' "$1" >> "$GITHUB_STEP_SUMMARY"
  fi
}

# Read live heads. Never enumerate tags or push to the upstream URL.
upstream_heads="$(git ls-remote --heads "$UPSTREAM_URL")"
git fetch --quiet --no-tags --prune origin '+refs/heads/*:refs/remotes/origin/*'

report '### Upstream branch synchronization'
report "Dry run: $DRY_RUN"
if [[ -n "${SYNC_TOKEN_SOURCE:-}" ]]; then
  report "Push credential: $SYNC_TOKEN_SOURCE"
fi
report ''
report '| Branch | Result |'
report '| --- | --- |'

created=0
updated=0
mirrored=0
unchanged=0
diverged=0
failed=0
ignored=0
while read -r upstream_sha source_ref; do
  [[ -n "$source_ref" ]] || continue
  branch="${source_ref#refs/heads/}"
  mirror_branch=false
  case "$branch" in
    dev|v3|v4|v5) mirror_branch=true ;;
  esac
  if [[ "$mirror_branch" == false && ! "$branch" =~ $version_pattern ]]; then
    ignored=$((ignored + 1))
    continue
  fi

  origin_sha=''
  if git show-ref --verify --quiet "refs/remotes/origin/$branch"; then
    origin_sha="$(git rev-parse "refs/remotes/origin/$branch")"
  fi
  if [[ "$origin_sha" == "$upstream_sha" ]]; then
    report "| $branch | Unchanged |"
    unchanged=$((unchanged + 1))
    continue
  fi

  # Fetch only matching branches that need inspection, without checking out their code.
  source_local_ref="refs/remotes/version-sync/$branch"
  git fetch --quiet --no-tags "$UPSTREAM_URL" \
    "+$source_ref:$source_local_ref"
  upstream_sha="$(git rev-parse "$source_local_ref")"
  if [[ "$origin_sha" == "$upstream_sha" ]]; then
    report "| $branch | Unchanged |"
    unchanged=$((unchanged + 1))
    continue
  fi

  operation=Create
  push_options=(--porcelain)
  if [[ "$mirror_branch" == true ]]; then
    # Only these four branches discard origin-only commits. The explicit lease
    # rejects concurrent changes, including creation of a previously absent branch.
    push_options+=("--force-with-lease=refs/heads/$branch:$origin_sha")
    if [[ -n "$origin_sha" ]]; then
      operation='Mirror upstream (discard origin-only commits)'
    fi
  elif [[ -n "$origin_sha" ]]; then
    if git merge-base --is-ancestor "$origin_sha" "$upstream_sha"; then
      operation=Update
    else
      status=$?
      if [[ "$status" != 1 ]]; then
        exit "$status"
      fi
      report "| $branch | Skipped: origin has commits absent from upstream |"
      diverged=$((diverged + 1))
      continue
    fi
  fi

  if [[ "$DRY_RUN" == true ]]; then
    report "| $branch | Would $operation |"
  elif push_output="$(LC_ALL=C git -c push.followTags=false push "${push_options[@]}" origin \
    "$upstream_sha:refs/heads/$branch" 2>&1)"; then
    printf '%s\n' "$push_output"
    report "| $branch | $operation succeeded |"
  else
    printf '%s\n' "$push_output" >&2
    failed=$((failed + 1))
    case "$push_output" in
      *'Permission to '*' denied to '*|*'Authentication failed'*|\
      *'Permission denied (publickey)'*|\
      *'The requested URL returned error: 401'*|*'The requested URL returned error: 403'*)
        report "| $branch | FAILED to $operation: origin denied authentication or repository write access |"
        report ''
        report 'Sync stopped: remaining branches were not attempted because origin rejected the push credential.'
        report 'For GitHub Actions, SYNC_BRANCHES_TOKEN overrides GITHUB_TOKEN. Check the token owner has Write access to the target repository, the token includes this repository with Contents and Workflows write permissions, and required organization approval/SSO authorization is complete.'
        report 'The workflow contents: write permission applies only to GITHUB_TOKEN; it cannot grant permissions to a PAT. See .github/sync-version-branches.md for setup.'
        break
        ;;
    esac
    report "| $branch | FAILED to $operation; check concurrent changes, push permissions or branch protection |"
    continue
  fi
  if [[ "$operation" == Create ]]; then
    created=$((created + 1))
  elif [[ "$mirror_branch" == true ]]; then
    mirrored=$((mirrored + 1))
  else
    updated=$((updated + 1))
  fi
done <<< "$upstream_heads"

report ''
report "Create: $created; update: $updated; mirror: $mirrored; unchanged: $unchanged; skipped: $diverged; failed: $failed; ignored branches: $ignored."
[[ "$failed" == 0 ]]
