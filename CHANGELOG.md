# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Multi-prefix per RA: a Border Router that advertises multiple ULA prefixes or routes in a single Router Advertisement now gets all of them configured (previously only the last one was). Affects `PacketParser` output shape: `prefixes` and `routes` are now lists.
- Operator warning when the same prefix is later advertised by a different router. The OS route is silently replaced by `ip route add`; the warning surfaces failover or misconfiguration.
- `CLEANUP_PREFIX_LENGTHS` env var on `bin/configure-ipv6-route.sh` to override the default `"64 48 32 16"` set of prefix lengths cleaned up before installing a new route.
- MIT `LICENSE`. The project was previously unlicensed, which legally blocked adoption.

### Fixed
- `--enable-rs` no longer crashes with `AttributeError` (`RouterSolicitor.send_solicitation()` was called as `.send()`).
- `--debug` now actually emits debug-level logs without also requiring `--verbose`.
- `bin/start.sh` now respects `-i`/`--interface` (was hardcoded to `ovs_eth2`).
- README documented a `--log-ignored` flag that does not exist; removed.

### Removed
- Four unused modules (`packet_handler.py`, `packet_filter.py`, `route_info.py`, `router_discovery.py`) that were not wired into the active code path.

## [0.1.0] - Unreleased

Initial MVP with end-to-end RA listening and route configuration. Not yet tagged.
