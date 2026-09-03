#!/usr/bin/env python3
"""UNFORGE Trail — itinerary of one-passage stamps.

Compares SHA-256 across cards. Does not sign. Does not open a signature.
No node. No cloud. No coin.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

FORMAT = "UNFORGE-TRAIL-v1"
FORMAT_P = "UNFORGE-PREUVE-v1"
FORMAT_R = "UNFORGE-RETRAIT-v1"
SCHEMA_ID = "trail.v0"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema" / "trail.v0.json"

VERT = "\033[38;2;57;255;136m"
ROUGE = "\033[38;2;255;77;79m"
AMBRE = "\033[38;2;245;200;66m"
RESET = "\033[0m"


def empreinte_flux(paquet: dict) -> str:
    """SHA-256(fait|prev|token_id). Public card binding. Not a seal."""
    return hashlib.sha256(
        f"{paquet.get('fait') or ''}|{paquet.get('prev') or ''}|{paquet.get('token_id') or ''}".encode()
    ).hexdigest()


def phrase_trail(rec: dict) -> str:
    err = rec.get("erreur")
    phrases = {
        "format": "pas UNFORGE-TRAIL-v1.",
        "itinéraire vide": "itinéraire vide.",
        "itinéraire introuvable": "itinéraire introuvable.",
        "json": "JSON illisible.",
        "preuve manquante": "preuve manquante.",
        "format carte": "une étape n'est pas UNFORGE-PREUVE-v1.",
        "sans sha256": "étape sans sha256.",
        "sans id": "étape sans id.",
        "passage déjà brûlé": "un tampon a déjà brûlé ce passage.",
        "sha divergents": "les tampons ne nomment pas le même fichier.",
    }
    if err in phrases:
        base = phrases[err]
    elif err and err.startswith("preuve manquante"):
        base = "preuve manquante."
    elif err and "sans sha256" in err:
        base = "étape sans sha256."
    elif rec.get("empreinte_ok") is False:
        base = "l'empreinte ne tient pas."
    elif rec.get("fichier_ok") is False:
        base = "le fichier ne correspond pas à l'itinéraire."
    elif rec.get("ok") and rec.get("fichier_ok") is None:
        base = "l'itinéraire tient. aucun fichier présenté."
    elif rec.get("ok"):
        base = "l'itinéraire tient. chaque tampon est un passage."
    elif err:
        base = str(err)
    else:
        base = "refus."
    extras: list[str] = []
    for rt in rec.get("retraits") or []:
        if rt.get("ok") is False:
            extras.append("retrait illisible.")
        elif rt.get("ok") is True:
            extras.append("retrait à côté ; l'histoire reste.")
    return " ".join([base, *extras])


def habiller(rec: dict) -> dict:
    rec.setdefault("geste", "trail")
    rec.setdefault("marque", "UNFORGE")
    rec.setdefault("noeud", "non requis")
    rec.setdefault("schema", SCHEMA_ID)
    rec["phrase"] = phrase_trail(rec)
    return rec


def lier_retrait(preuve: dict, chemin: Path) -> dict:
    """Bind a UNFORGE-RETRAIT-v1 to the card. Does not verify a signature."""
    rt = json.loads(chemin.read_text(encoding="utf-8"))
    if rt.get("format") != FORMAT_R:
        return {"ok": False, "erreur": "format", "chemin": str(chemin)}
    cible = rt.get("empreinte_cible") or rt.get("empreinte")
    ok = (
        rt.get("card_id") == preuve.get("card_id")
        and rt.get("preuve_id") == preuve.get("id")
        and cible == preuve.get("empreinte")
    )
    return {
        "ok": ok,
        "statut": "retiré" if ok else "retrait-invalide",
        "preuve_id": preuve.get("id"),
        "histoire": "la preuve reste ; le retrait s'ajoute",
        "chemin": str(chemin),
    }


def voisin_retrait(preuve: Path, etape: dict, racine: Path) -> Path | None:
    nom = etape.get("retrait")
    if nom:
        p = (racine / nom).resolve()
        return p if p.is_file() else None
    for c in (
        Path(str(preuve) + ".retrait.json"),
        preuve.with_name(preuve.name.replace(".unforge.json", ".retrait.json")),
    ):
        if c.is_file():
            return c
    return None


def verifier(trail: Path, fichier: Path | None = None) -> dict:
    """Walk the itinerary. Local. No server. Does not sign. Agents: this is the hook."""
    try:
        paquet = json.loads(trail.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return habiller({"ok": False, "erreur": "json", "detail": str(e)})
    if paquet.get("format") != FORMAT:
        return habiller({"ok": False, "erreur": "format"})
    etapes = paquet.get("etapes")
    if not isinstance(etapes, list) or not etapes:
        return habiller({"ok": False, "erreur": "itinéraire vide", "etapes": 0})

    shas: list[str] = []
    ids: list[str] = []
    card_ids: list[str | None] = []
    token_ids: list[str | None] = []
    gestes: list[str | None] = []
    passages: list[dict] = []
    retraits: list[dict] = []
    vus: set[str] = set()
    flux: list[bool] = []
    racine = trail.parent

    for i, etape in enumerate(etapes):
        if not isinstance(etape, dict):
            return habiller({"ok": False, "erreur": "format carte", "etape": i})
        pp = (racine / (etape.get("preuve") or "")).resolve()
        if not pp.is_file():
            return habiller({"ok": False, "erreur": "preuve manquante", "etape": i, "attendu": str(pp)})
        try:
            pr = json.loads(pp.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            return habiller({"ok": False, "erreur": "json", "etape": i, "detail": str(e)})
        if pr.get("format") != FORMAT_P:
            return habiller({"ok": False, "erreur": "format carte", "etape": i})
        ident = pr.get("id")
        if not ident:
            return habiller({"ok": False, "erreur": "sans id", "etape": i})
        if ident in vus:
            return habiller({"ok": False, "erreur": "passage déjà brûlé", "id": ident, "etape": i})
        vus.add(ident)
        sha = (pr.get("objet") or {}).get("sha256")
        if not sha:
            return habiller({"ok": False, "erreur": "sans sha256", "etape": i})
        emp_ok = None
        if "fait" in pr:
            emp_ok = empreinte_flux(pr) == pr.get("empreinte")
            flux.append(bool(emp_ok))
        rt_path = voisin_retrait(pp, etape, racine)
        retrait = lier_retrait(pr, rt_path) if rt_path is not None else None
        if retrait is not None:
            retraits.append(retrait)
        shas.append(sha)
        ids.append(ident)
        card_ids.append(pr.get("card_id"))
        token_ids.append(pr.get("token_id"))
        gestes.append(etape.get("geste"))
        passages.append(
            {
                "geste": etape.get("geste"),
                "id": ident,
                "card_id": pr.get("card_id"),
                "token_id": pr.get("token_id"),
                "sha256": sha,
                "octets": (pr.get("objet") or {}).get("octets"),
                "empreinte": pr.get("empreinte"),
                "empreinte_ok": emp_ok,
                "retrait": None if retrait is None else retrait.get("statut"),
            }
        )

    meme = len(set(shas)) == 1
    if not meme:
        return habiller(
            {
                "ok": False,
                "erreur": "sha divergents",
                "etapes": len(etapes),
                "ids": ids,
                "sha256": None,
                "meme_fichier": False,
                "passages": passages,
            }
        )

    empreinte_ok: bool | None
    if not flux:
        empreinte_ok = None
    else:
        empreinte_ok = all(flux)

    fichier_ok = None
    sha_fichier = None
    octets = None
    if fichier is not None:
        brut = fichier.read_bytes()
        sha_fichier = hashlib.sha256(brut).hexdigest()
        octets = len(brut)
        attendu_octets = passages[0].get("octets")
        octets_ok = attendu_octets in (None, octets)
        fichier_ok = sha_fichier == shas[0] and octets_ok

    ok = bool(meme and empreinte_ok is not False and fichier_ok is not False)
    return habiller(
        {
            "ok": ok,
            "etapes": len(etapes),
            "ids": ids,
            "card_ids": card_ids,
            "token_ids": token_ids,
            "gestes": gestes,
            "sha256": shas[0],
            "sha256_fichier": sha_fichier,
            "octets": octets,
            "meme_fichier": meme,
            "passage_unique": True,
            "fichier_ok": fichier_ok,
            "empreinte_ok": empreinte_ok,
            "retraits": retraits,
            "passages": passages,
        }
    )


verify = verifier


def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def voisin_trail(fichier: Path) -> Path:
    for c in (
        Path(str(fichier) + ".unforge-trail.json"),
        fichier.with_name(fichier.stem + ".unforge-trail.json"),
    ):
        if c.is_file():
            return c
    raise FileNotFoundError("itinéraire introuvable")


def resoudre(chemins: list[Path]) -> tuple[Path, Path | None]:
    """Pick the itinerary and the optional file."""
    if len(chemins) == 1:
        seul = chemins[0]
        if seul.name.endswith(".unforge-trail.json"):
            return seul, None
        return voisin_trail(seul), seul
    trail = next((c for c in chemins if c.name.endswith(".unforge-trail.json")), chemins[0])
    fichier = next((c for c in chemins if c != trail), None)
    return trail, fichier


def code_sortie(rec: dict) -> int:
    err = rec.get("erreur")
    if err in {"itinéraire introuvable", "json", "fichier introuvable"}:
        return 2
    return 0 if rec.get("ok") else 1


def _colorer() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stderr.isatty() or sys.stdout.isatty()


def ligne_verdict(rec: dict, color: bool) -> str:
    if rec.get("ok") and rec.get("retraits"):
        mot, teinte = "AMBRE", AMBRE
    elif rec.get("ok"):
        mot, teinte = "VERT", VERT
    else:
        mot, teinte = "ROUGE", ROUGE
    if color:
        mot = f"{teinte}{mot}{RESET}"
    return f"{mot} {rec.get('phrase')}"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="trail.py",
        description="UNFORGE Trail — verify a file's itinerary of one-passage stamps. No node. Does not sign.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  python3 trail.py examples/bienvenue.txt\n"
            "  python3 trail.py examples/bienvenue.unforge-trail.json examples/bienvenue.txt\n"
            "  python3 trail.py --schema\n"
            "\n"
            "If the itinerary path is omitted, Trail looks for FILE.unforge-trail.json\n"
            "or <stem>.unforge-trail.json beside the file.\n"
            "Exit 0 = itinerary holds. Exit 1 = refuse. Exit 2 = unreadable.\n"
            "Agents: python3 trail.py --schema or from trail import verifier"
        ),
    )
    p.add_argument("paths", nargs="*", metavar="FILE", help="file, and/or its .unforge-trail.json")
    p.add_argument("--schema", action="store_true", help="print trail.v0 JSON Schema and exit")
    sortie = p.add_mutually_exclusive_group()
    sortie.add_argument("--json", action="store_true", help="machine record on stdout (default)")
    sortie.add_argument("--human", action="store_true", help="one VERT / ROUGE / AMBRE verdict")
    args = p.parse_args(argv)

    if args.schema:
        try:
            print(json.dumps(schema(), ensure_ascii=False, indent=2))
        except Exception as e:
            print(json.dumps({"ok": False, "erreur": str(e)}, ensure_ascii=False, indent=2))
            return 2
        return 0

    if not args.paths:
        p.error("drop a file, or a trail and its file")

    chemins = [Path(x) for x in args.paths]
    try:
        trail, fichier = resoudre(chemins)
        if not trail.is_file():
            rec = habiller({"ok": False, "erreur": "itinéraire introuvable", "attendu": str(trail)})
            print(json.dumps(rec, ensure_ascii=False, indent=2))
            return 2
        if fichier is not None and not fichier.is_file():
            rec = habiller({"ok": False, "erreur": "fichier introuvable", "attendu": str(fichier)})
            print(json.dumps(rec, ensure_ascii=False, indent=2))
            return 2
        rec = verifier(trail, fichier)
    except FileNotFoundError:
        rec = habiller({"ok": False, "erreur": "itinéraire introuvable"})
        print(json.dumps(rec, ensure_ascii=False, indent=2))
        return 2
    except json.JSONDecodeError as e:
        rec = habiller({"ok": False, "erreur": "json", "detail": str(e)})
        print(json.dumps(rec, ensure_ascii=False, indent=2))
        return 2
    except Exception as e:
        rec = habiller({"ok": False, "erreur": str(e)})
        print(json.dumps(rec, ensure_ascii=False, indent=2))
        return 2

    if args.human:
        print(ligne_verdict(rec, _colorer()))
    else:
        print(json.dumps(rec, ensure_ascii=False, indent=2))
    return code_sortie(rec)


if __name__ == "__main__":
    raise SystemExit(main())
