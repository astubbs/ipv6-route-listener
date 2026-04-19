# Architecture

Developer-facing implementation doc. Complements the user-facing `README.md`.

## Problem statement

Linux kernels need `CONFIG_IPV6_ROUTE_INFO` to autoconfigure routes from ICMPv6 Route Information Options (RFC 4191). Synology DSM ships kernels without this option, which means Thread Border Routers can advertise ULA routes to Matter devices but the host never installs them - Home Assistant on Synology can't reach the devices.

This project is a userspace workaround: sniff RAs with Scapy, extract the ULA prefixes/routes, and call `ip -6 route` directly.

## Module map

```
route_listener/
├── main.py              CLI entry point + argparse + wiring
├── config.py            DEFAULT_INTERFACE, log file constants
├── logger.py            Logger wrapper (drop-in for stdlib logging.Logger)
├── packet_parser.py     PacketParser - Scapy packet -> dict
├── route_configurator.py RouteConfigurator + RouteExecutor + Route dataclass
├── router_solicitor.py  Sends ICMPv6 Router Solicitation (when --enable-rs)
└── scapy_handler.py     ScapyPacketHandler - sniff loop, dispatches to parser/configurator

bin/
├── start.sh                  Docker entrypoint, parses -i/--interface
└── configure-ipv6-route.sh   Shell script that runs `ip -6 route ...`
```

## Data flow

```
NIC (interface)
   │  scapy sniff(iface, filter="icmp6 and ip6[40] = 134")
   ▼
ScapyPacketHandler._handle_packet(packet)
   │  filters non-IPv6 / non-RA
   ▼
PacketParser.parse(packet)
   │  walks ra.payload, dispatching ICMPv6NDOptPrefixInfo / ICMPv6NDOptRouteInfo
   │  -> {"src_ip", "prefixes": [...], "routes": [...]}
   ▼
RouteConfigurator.process_packet_info(packet_info)
   │  iterates prefixes/routes, filters non-ULA, calls configure() per ULA entry
   ▼
RouteConfigurator.configure(prefix, prefix_len, router, is_prefix)
   │  dedup via seen_routes set
   │  router-change warning via prefix_to_router map
   ▼
RouteExecutor.execute(route, prefix_len)
   │  sets PREFIX/PREFIX_LEN/IFACE/ROUTER/IS_PREFIX env vars
   │  optionally inherits CLEANUP_PREFIX_LENGTHS from process env
   ▼
bin/configure-ipv6-route.sh
   │  validates inputs, removes existing routes for the prefix, then:
   ▼
ip -6 route add <prefix>/<len> via <router> dev <iface> [onlink]
```

## Key design decisions

**Scapy for capture.** Need access to raw ICMPv6 RA bytes including all option types (PIO, RIO, source link-layer address, etc.). Scapy's dissector handles this and lets us construct test packets in-process for integration tests.

**Shell script for routing commands.** The `ip` command must run with `NET_ADMIN` capability. Centralizing the actual route mutations in a shell script keeps the privileged code path isolated and auditable, and lets the script be tested independently.

**ULA-only filtering.** Matter/Thread devices use ULA (Unique Local Address, `fd00::/8`) prefixes. Filtering anything else avoids accidentally re-routing global IPv6 traffic through the Border Router.

**Lists for prefixes/routes (not single keys).** A real Border Router can advertise multiple `PrefixInfo` and `RouteInfo` options in one RA. The earlier single-key shape silently dropped all but the last; the parser now returns lists and the configurator iterates them.

**Per-router prefix tracking.** `RouteConfigurator.prefix_to_router` maps a base prefix to the most recent advertising router. When a new RA from a different router arrives for a known prefix, the existing OS route is replaced (silently) - the configurator logs an error so operators can see failover or misconfiguration events.

**Logger as drop-in for stdlib logging.Logger.** Method names `setLevel` and `isEnabledFor` are intentional camelCase (with `# noqa: N802`) so callers can pass the wrapper anywhere a stdlib `Logger` is expected.

**`tests/` is a Python package.** Has `__init__.py` so the mypy `tests.*` override matches; otherwise mypy treats each test file as its own top-level module and the override doesn't apply.

## CI workflow set

Workflows in `.github/workflows/`:

- `verify.yml` - format / import sort / mypy / pytest / lint. Runs on push to main and on every PR. The `make verify-check` target mirrors this exactly.
- `pr-quality.yml` - duplicate-detection (PMD CPD + jscpd), file-similarity, dependency review. PR-only. Tight thresholds calibrated to the current zero-clone baseline (1% absolute, 0% regression).
- `claude-code-review.yml` - auto Claude Code review on PR open/sync.
- `claude.yml` - interactive `@claude` mentions on issues and PR comments.
- `release.yml` - triggered by pushing a `vX.Y.Z` tag. Verifies the tag matches `pyproject.toml` version, builds + publishes the Python package to PyPI via OIDC trusted publishing, and builds + publishes a multi-arch Docker image to GHCR and Docker Hub.

The Claude workflows require a `CLAUDE_CODE_OAUTH_TOKEN` repo secret; without it they fail at the action invocation. The release workflow requires one-time setup on PyPI (trusted publishing) and Docker Hub (`DOCKERHUB_USERNAME` + `DOCKERHUB_TOKEN` secrets) - see the workflow file's header comment for details.

## Extension points

- **New RA option types** - add an `isinstance(opt, ...)` branch in `PacketParser._process_option` and an entry in the `packet_info` dict shape, plus iteration in `RouteConfigurator.process_packet_info`.
- **Different prefix filter** - `RouteConfigurator.process_packet_info` does the `startswith("fd")` check inline; centralize in a method if you need more complex rules.
- **Different routing backend** - replace `RouteExecutor` (which calls the shell script) with another implementation. The script is the only thing that touches the kernel routing table.
- **CLI flags** - add to `argparse` in `main.py`, then thread through `ScapyPacketHandler` constructor.
