# UNFORGE Trail

One file. Several passages. Each stamp burned once.

```bash
python3 trail.py examples/bienvenue.txt
python3 trail.py examples/bienvenue.unforge-trail.json examples/bienvenue.txt
```

`ok: true` — every stamp names the same SHA-256, and each id burned once.
Trail compares the itinerary. It does not sign. It does not open a signature.

Agents and other tools — no server:

```bash
python3 trail.py --schema
```

`from trail import verifier`. See [INTEROP.md](INTEROP.md).

Each proof stays a one-passage card
([check](https://github.com/carllaliberte/unforge-check) ·
[press](https://github.com/carllaliberte/unforge-press) ·
[retract](https://github.com/carllaliberte/unforge-retract)).
No node. No cloud. No coin.
Brand UNFORGE reserved. Code: Apache-2.0.
