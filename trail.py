#!/usr/bin/env python3
"""UNFORGE Trail — itinerary of one-passage stamps."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
FORMAT = "UNFORGE-TRAIL-v1"
def verifier(trail: Path, fichier: Path | None) -> dict:
    paquet = json.loads(trail.read_text(encoding="utf-8"))
    if paquet.get("format") != FORMAT:
        return {"ok": False, "erreur": "format"}
    etapes = paquet.get("etapes") or []
    shas, ids, gestes = [], [], []
    for i, etape in enumerate(etapes):
        pp = (trail.parent / (etape.get("preuve") or "")).resolve()
        if not pp.is_file():
            return {"ok": False, "erreur": f"preuve manquante {i}"}
        pr = json.loads(pp.read_text(encoding="utf-8"))
        sha = (pr.get("objet") or {}).get("sha256")
        if not sha:
            return {"ok": False, "erreur": f"étape {i} sans sha256"}
        shas.append(sha); ids.append(pr.get("id")); gestes.append(etape.get("geste"))
    meme = len(set(shas)) == 1 if shas else False
    fichier_ok = None
    if fichier is not None:
        fichier_ok = hashlib.sha256(fichier.read_bytes()).hexdigest() == shas[0]
    return {"ok": bool(meme and fichier_ok is not False), "etapes": len(etapes), "ids": ids, "sha256": shas[0] if shas else None, "meme_fichier": meme, "fichier_ok": fichier_ok, "geste": gestes, "marque": "UNFORGE"}
def main():
    p = argparse.ArgumentParser(); p.add_argument("trail"); p.add_argument("fichier", nargs="?")
    a = p.parse_args()
    rec = verifier(Path(a.trail), Path(a.fichier) if a.fichier else None)
    print(json.dumps(rec, ensure_ascii=False, indent=2))
    return 0 if rec.get("ok") else 1
if __name__ == "__main__":
    raise SystemExit(main())
