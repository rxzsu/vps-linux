<!-- Title: <area>: <imperative summary> -->

## What

<!-- One paragraph: what changes and why. -->

## Validation performed

<!-- Exact commands and exit statuses. A build exit status is not boot verification. -->

- [ ] `./tests/static-checks.sh` (for build system/config changes)
- [ ] `cargo +1.99.0 fmt/clippy/deny/test` + packaging tests (for vpsctl changes)
- [ ] VM smoke/acceptance where the change affects first boot or the image

## Not validated / known limits

<!-- State honestly what was NOT run. Do not mark unrun checks as passed. -->

## Checklist

- [ ] No published release assets are modified
- [ ] No secrets, generated artifacts or host-specific data committed
- [ ] Documentation updated where behavior changed
