#!/usr/bin/env python3
"""Public itinerary tests. Never issue. Never invent a valid signature."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trail import (  # noqa: E402
    SCHEMA_ID,
    code_sortie,
    empreinte_flux,
    habiller,
    phrase_trail,
    resoudre,
    schema,
    verifier,
    voisin_trail,
)

FICHIER = ROOT / "examples" / "bienvenue.txt"
TRAIL = ROOT / "examples" / "bienvenue.unforge-trail.json"
CARTE = ROOT / "examples" / "bienvenue.txt.unforge.json"
PY = sys.executable
SHA = "e8fe730c49dc859358e3b94376fb0a5f0916aca21b18457eb3d8391c4ebc0838"


def _run(args: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(
        [PY, str(ROOT / "trail.py"), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        **kw,
    )


def _carte(ident: str, sha: str = SHA, octets: int = 92, **extra) -> dict:
    rec = {
        "format": "UNFORGE-PREUVE-v1",
        "marque": "UNFORGE",
        "id": ident,
        "card_id": "QT-EM-DEMO0001",
        "token_id": f"tok-{ident}",
        "empreinte": extra.pop("empreinte", "demo"),
        "objet": {"nom": "bienvenue.txt", "octets": octets, "sha256": sha},
    }
    rec.update(extra)
    return rec


def _pack(tmp: Path, etapes: list[dict], cartes: dict[str, dict]) -> Path:
    for nom, paquet in cartes.items():
        (tmp / nom).write_text(json.dumps(paquet), encoding="utf-8")
    dest = tmp / "itineraire.unforge-trail.json"
    dest.write_text(
        json.dumps({"format": "UNFORGE-TRAIL-v1", "marque": "UNFORGE", "etapes": etapes}),
        encoding="utf-8",
    )
    return dest


class ItinerairePublic(unittest.TestCase):
    def test_exemple_tient(self):
        rec = verifier(TRAIL, FICHIER)
        self.assertTrue(rec["ok"])
        self.assertTrue(rec["fichier_ok"])
        self.assertTrue(rec["meme_fichier"])
        self.assertTrue(rec["passage_unique"])
        self.assertEqual(rec["geste"], "trail")
        self.assertEqual(rec["schema"], SCHEMA_ID)
        self.assertEqual(rec["noeud"], "non requis")
        self.assertEqual(rec["etapes"], 1)
        self.assertEqual(rec["ids"], ["QT-PR-DEMO0001"])
        self.assertEqual(rec["card_ids"], ["QT-EM-DEMO0001"])
        self.assertEqual(rec["token_ids"], ["QT-JK-DEMO0001"])
        self.assertEqual(rec["gestes"], ["créé"])
        self.assertEqual(rec["sha256"], SHA)
        self.assertEqual(rec["octets"], FICHIER.stat().st_size)
        self.assertIsNone(rec["empreinte_ok"])
        self.assertEqual(rec["retraits"], [])
        self.assertEqual(rec["phrase"], "l'itinéraire tient. chaque tampon est un passage.")

    def test_sans_fichier(self):
        rec = verifier(TRAIL, None)
        self.assertTrue(rec["ok"])
        self.assertIsNone(rec["fichier_ok"])
        self.assertEqual(rec["phrase"], "l'itinéraire tient. aucun fichier présenté.")

    def test_fichier_altéré(self):
        with tempfile.TemporaryDirectory() as tmp:
            copie = Path(tmp) / "x.txt"
            copie.write_bytes(FICHIER.read_bytes() + b"\n")
            rec = verifier(TRAIL, copie)
            self.assertFalse(rec["ok"])
            self.assertFalse(rec["fichier_ok"])
            self.assertTrue(rec["meme_fichier"])
            self.assertEqual(rec["phrase"], "le fichier ne correspond pas à l'itinéraire.")
            self.assertEqual(code_sortie(rec), 1)

    def test_format_refusé(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "x.unforge-trail.json"
            p.write_text(json.dumps({"format": "NON", "etapes": []}), encoding="utf-8")
            rec = verifier(p, None)
            self.assertFalse(rec["ok"])
            self.assertEqual(rec["erreur"], "format")
            self.assertEqual(rec["phrase"], "pas UNFORGE-TRAIL-v1.")

    def test_itinéraire_vide(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = _pack(Path(tmp), [], {})
            dest.write_text(
                json.dumps({"format": "UNFORGE-TRAIL-v1", "etapes": []}),
                encoding="utf-8",
            )
            rec = verifier(dest, None)
            self.assertFalse(rec["ok"])
            self.assertEqual(rec["erreur"], "itinéraire vide")

    def test_preuve_manquante(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = _pack(Path(tmp), [{"geste": "créé", "preuve": "absent.unforge.json"}], {})
            rec = verifier(dest, None)
            self.assertFalse(rec["ok"])
            self.assertEqual(rec["erreur"], "preuve manquante")
            self.assertEqual(rec["phrase"], "preuve manquante.")

    def test_carte_mauvais_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = _pack(
                Path(tmp),
                [{"geste": "créé", "preuve": "a.unforge.json"}],
                {"a.unforge.json": {"format": "NON", "id": "x", "objet": {"sha256": SHA}}},
            )
            rec = verifier(dest, None)
            self.assertFalse(rec["ok"])
            self.assertEqual(rec["erreur"], "format carte")

    def test_sans_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = _pack(
                Path(tmp),
                [{"geste": "créé", "preuve": "a.unforge.json"}],
                {"a.unforge.json": _carte("", sha=SHA)},
            )
            rec = verifier(dest, None)
            self.assertFalse(rec["ok"])
            self.assertEqual(rec["erreur"], "sans id")

    def test_sans_sha(self):
        with tempfile.TemporaryDirectory() as tmp:
            carte = _carte("A")
            carte["objet"] = {"nom": "x"}
            dest = _pack(
                Path(tmp),
                [{"geste": "créé", "preuve": "a.unforge.json"}],
                {"a.unforge.json": carte},
            )
            rec = verifier(dest, None)
            self.assertFalse(rec["ok"])
            self.assertEqual(rec["erreur"], "sans sha256")

    def test_passage_déjà_brûlé(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = _pack(
                Path(tmp),
                [
                    {"geste": "créé", "preuve": "a.unforge.json"},
                    {"geste": "lu", "preuve": "b.unforge.json"},
                ],
                {"a.unforge.json": _carte("SAME"), "b.unforge.json": _carte("SAME")},
            )
            rec = verifier(dest, None)
            self.assertFalse(rec["ok"])
            self.assertEqual(rec["erreur"], "passage déjà brûlé")
            self.assertEqual(rec["phrase"], "un tampon a déjà brûlé ce passage.")

    def test_deux_passages_même_fichier(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = _pack(
                Path(tmp),
                [
                    {"geste": "créé", "preuve": "a.unforge.json"},
                    {"geste": "lu", "preuve": "b.unforge.json"},
                ],
                {"a.unforge.json": _carte("A"), "b.unforge.json": _carte("B")},
            )
            rec = verifier(dest, FICHIER)
            self.assertTrue(rec["ok"])
            self.assertEqual(rec["etapes"], 2)
            self.assertEqual(rec["ids"], ["A", "B"])
            self.assertTrue(rec["meme_fichier"])
            self.assertTrue(rec["fichier_ok"])

    def test_sha_divergents(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = _pack(
                Path(tmp),
                [
                    {"geste": "créé", "preuve": "a.unforge.json"},
                    {"geste": "lu", "preuve": "b.unforge.json"},
                ],
                {
                    "a.unforge.json": _carte("A", sha=SHA),
                    "b.unforge.json": _carte("B", sha="0" * 64),
                },
            )
            rec = verifier(dest, None)
            self.assertFalse(rec["ok"])
            self.assertEqual(rec["erreur"], "sha divergents")
            self.assertFalse(rec["meme_fichier"])

    def test_octets_refusent(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = _pack(
                Path(tmp),
                [{"geste": "créé", "preuve": "a.unforge.json"}],
                {"a.unforge.json": _carte("A", octets=1)},
            )
            rec = verifier(dest, FICHIER)
            self.assertFalse(rec["ok"])
            self.assertFalse(rec["fichier_ok"])


class FluxEtRetract(unittest.TestCase):
    def test_empreinte_flux_tient(self):
        fait = "constat de test"
        token = "tok-flux"
        emp = hashlib.sha256(f"{fait}||{token}".encode()).hexdigest()
        carte = _carte("FLUX", empreinte=emp, fait=fait, prev="", token_id=token)
        self.assertEqual(empreinte_flux(carte), emp)
        with tempfile.TemporaryDirectory() as tmp:
            dest = _pack(
                Path(tmp),
                [{"geste": "créé", "preuve": "a.unforge.json"}],
                {"a.unforge.json": carte},
            )
            rec = verifier(dest, FICHIER)
            self.assertTrue(rec["ok"])
            self.assertTrue(rec["empreinte_ok"])

    def test_empreinte_flux_cassée(self):
        carte = _carte("FLUX", empreinte="0" * 64, fait="x", prev="", token_id="t")
        with tempfile.TemporaryDirectory() as tmp:
            dest = _pack(
                Path(tmp),
                [{"geste": "créé", "preuve": "a.unforge.json"}],
                {"a.unforge.json": carte},
            )
            rec = verifier(dest, None)
            self.assertFalse(rec["ok"])
            self.assertFalse(rec["empreinte_ok"])
            self.assertEqual(rec["phrase"], "l'empreinte ne tient pas.")

    def test_retrait_lié(self):
        carte = _carte("R1", empreinte="abc")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dest = _pack(root, [{"geste": "créé", "preuve": "a.unforge.json"}], {"a.unforge.json": carte})
            (root / "a.unforge.json.retrait.json").write_text(
                json.dumps(
                    {
                        "format": "UNFORGE-RETRAIT-v1",
                        "preuve_id": "R1",
                        "card_id": "QT-EM-DEMO0001",
                        "empreinte_cible": "abc",
                    }
                ),
                encoding="utf-8",
            )
            rec = verifier(dest, None)
            self.assertTrue(rec["ok"], "retract does not erase the itinerary")
            self.assertEqual(len(rec["retraits"]), 1)
            self.assertTrue(rec["retraits"][0]["ok"])
            self.assertEqual(rec["retraits"][0]["statut"], "retiré")
            self.assertIn("l'histoire reste", rec["phrase"])

    def test_retrait_invalide_ne_forge_pas(self):
        carte = _carte("R1", empreinte="abc")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dest = _pack(
                root,
                [{"geste": "créé", "preuve": "a.unforge.json", "retrait": "mauvais.retrait.json"}],
                {"a.unforge.json": carte},
            )
            (root / "mauvais.retrait.json").write_text(
                json.dumps(
                    {
                        "format": "UNFORGE-RETRAIT-v1",
                        "preuve_id": "OTHER",
                        "card_id": "QT-EM-DEMO0001",
                        "empreinte_cible": "abc",
                    }
                ),
                encoding="utf-8",
            )
            rec = verifier(dest, None)
            self.assertTrue(rec["ok"])
            self.assertFalse(rec["retraits"][0]["ok"])
            self.assertIn("retrait illisible", rec["phrase"])


class Resoudre(unittest.TestCase):
    def test_voisin_stem(self):
        self.assertEqual(voisin_trail(FICHIER), TRAIL)
        trail, fichier = resoudre([FICHIER])
        self.assertEqual(trail, TRAIL)
        self.assertEqual(fichier, FICHIER)

    def test_trail_seul(self):
        trail, fichier = resoudre([TRAIL])
        self.assertEqual(trail, TRAIL)
        self.assertIsNone(fichier)

    def test_deux_chemins(self):
        trail, fichier = resoudre([FICHIER, TRAIL])
        self.assertEqual(trail, TRAIL)
        self.assertEqual(fichier, FICHIER)

    def test_voisin_absent(self):
        with self.assertRaises(FileNotFoundError):
            resoudre([ROOT / "README.md"])


class SchemaEtHabit(unittest.TestCase):
    def test_schema_fichier(self):
        s = schema()
        self.assertEqual(s["title"], "unforge.trail.v0")
        self.assertIn("ok", s["required"])
        self.assertIn("geste", s["required"])

    def test_habiller_erreur(self):
        rec = habiller({"ok": False, "erreur": "json"})
        self.assertEqual(rec["geste"], "trail")
        self.assertEqual(phrase_trail(rec), "JSON illisible.")


class CLI(unittest.TestCase):
    def test_couple_exit_0(self):
        r = _run([str(TRAIL), str(FICHIER)])
        self.assertEqual(r.returncode, 0, r.stderr)
        rec = json.loads(r.stdout)
        self.assertTrue(rec["ok"])
        self.assertEqual(rec["geste"], "trail")

    def test_voisin_une_commande(self):
        r = _run([str(FICHIER)])
        self.assertEqual(r.returncode, 0, r.stderr)
        rec = json.loads(r.stdout)
        self.assertTrue(rec["ok"])
        self.assertTrue(rec["fichier_ok"])

    def test_human(self):
        r = _run([str(FICHIER), "--human"], env={**os.environ, "NO_COLOR": "1"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("VERT", r.stdout)
        self.assertIn("l'itinéraire tient", r.stdout)
        self.assertNotIn("{", r.stdout)

    def test_schema_flag(self):
        r = _run(["--schema"])
        self.assertEqual(r.returncode, 0, r.stderr)
        rec = json.loads(r.stdout)
        self.assertEqual(rec["title"], "unforge.trail.v0")

    def test_sans_args(self):
        r = _run([])
        self.assertEqual(r.returncode, 2)
        self.assertIn("drop a file", r.stderr)

    def test_fichier_altéré_exit_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            copie = Path(tmp) / "x.txt"
            copie.write_text("pas le fichier de l'itinéraire\n", encoding="utf-8")
            r = _run([str(TRAIL), str(copie)])
            self.assertEqual(r.returncode, 1)
            rec = json.loads(r.stdout)
            self.assertFalse(rec["ok"])
            self.assertFalse(rec["fichier_ok"])

    def test_itinéraire_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            seul = Path(tmp) / "orphelin.txt"
            seul.write_text("x", encoding="utf-8")
            r = _run([str(seul)])
            self.assertEqual(r.returncode, 2)
            rec = json.loads(r.stdout)
            self.assertEqual(rec["erreur"], "itinéraire introuvable")


if __name__ == "__main__":
    unittest.main()
