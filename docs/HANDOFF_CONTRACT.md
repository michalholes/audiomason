# 🧭 AudioMason – AUTHORITATIVE HANDOFF / AI CONTRACT

TENTO HANDOFF JE AUTHORITATIVE.
PLATIA PRAVIDLÁ Z TOHTO DOKUMENTU.
AK JE ROZPOR S INÝMI TEXTAMI, VYHRÁVA TENTO HANDOFF.

Komunikácia prebieha v slovenčine.

## PROJEKT
- Repo: michalholes/audiomason
- Branch: main
- Python: 3.11+
- Platforma: Debian / Ubuntu

Práca vždy vo venv:
. .venv/bin/activate
deactivate

## SCOPE (STRICT)
- Rieši sa iba explicitne zadaný cieľ
- Žiadne refaktory mimo nutného zásahu
- Žiadne „vylepšenia navyše“
- Žiadne dokumentačné zmeny, ak nie sú výslovne zadané

## AUTHORITATIVE FILE RULE (FAIL FAST)
- Vložený / uploadnutý súbor je AUTHORITATIVE
- Ak chýba potrebný súbor → FAIL FAST, vyžiadať ho
- Nehádať, nevymýšľať

## PATCHOVANIE (NEVYJEDNÁVATEĽNÉ)
- NO diff patches
- NO heredoc
- NO manuálne edit pokyny
- IBA deterministický Python patch skript:
  tools/patches/issue_<N>.py

Patch skript MUSÍ:
- anchor checks
- idempotency
- fail-fast
- post-edit assertions

Patch skripty sa DODÁVAJÚ AKO DOWNLOAD, nie copy-paste.
Po úspechu sa patch skript MUSÍ zmazať.

## GIT WORKFLOW (KANONICKÝ, BEZPEČNÝ)

```sh
python tools/patches/issue_<N>.py \
rm tools/patches/issue_<N>.py  \
python -m pytest -q && \
git add -A && \
git commit -m "<message>" && \
python -m pytest -q && \
git push

