# Interop — no server

Other agents and tools verify an itinerary with a local process. No node. No cloud. No coin. Nothing here signs.

Trail walks one-passage cards. It does not merge [check](https://github.com/carllaliberte/unforge-check), [press](https://github.com/carllaliberte/unforge-press), or [retract](https://github.com/carllaliberte/unforge-retract). The card is the join:

| Rail | What it does with the card |
|---|---|
| Trail | itinerary — same SHA-256, each `id` burned once |
| Check | one card — empreinte + signature + file |
| Press | print ids (`id`, `card_id`, `token_id`, SHA) |
| Retract | withdrawal sits beside the proof; history stays |

## Command

```bash
python3 trail.py FILE
python3 trail.py FILE.unforge-trail.json FILE
python3 trail.py --schema
```

`FILE` alone looks for `FILE.unforge-trail.json` or `<stem>.unforge-trail.json` beside it.

## Python

```python
from pathlib import Path
from trail import verifier, schema

rec = verifier(Path("doc.unforge-trail.json"), Path("doc.pdf"))
assert rec["ok"] is True          # only pass signal for the itinerary
schema()                          # trail.v0
```

`verify`, `resoudre`, `empreinte_flux` stay importable.

## Exit

| Code | Meaning |
|---|---|
| 0 | itinerary holds (`ok: true`) |
| 1 | refuse (format, empty, missing stamp, duplicate id, divergent SHA, file, broken flux) |
| 2 | unreadable (missing path, bad JSON) |

`ok: true` is the only success signal **for the itinerary**. A retract beside a stamp is noted (`retraits`). History stays. The file is not erased.

## Record

JSON on stdout. Shape: `schema/trail.v0.json`. Stable keys: `ok`, `geste`, `schema`, `etapes`, `ids`, `card_ids`, `token_ids`, `sha256`, `meme_fichier`, `passage_unique`, `fichier_ok`, `empreinte_ok`, `marque`, `noeud`, `phrase`. Extra keys may appear. `--human` prints VERT / ROUGE / AMBRE instead of JSON.

`empreinte_ok` is the public flux `SHA-256(fait|prev|token_id)` when `fait` is on the card. It is not a seal. Cards without `fait` leave it `null`.

## Do not

Stand up a server. Open `quantum.db`. Invent a signature. Call this a coin. Vendor famille or garde. Merge check, press, or retract into this repo.
