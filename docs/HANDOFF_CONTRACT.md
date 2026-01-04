````md
# 🧭 AudioMason – AUTHORITATIVE HANDOFF / AI CONTRACT (v2)

TENTO DOKUMENT JE AUTHORITATIVE PRE PRÁCU NA PROJEKTE AudioMason.
PLATÍ PRE VŠETKY IMPLEMENTAČNÉ CHATY, AK HANDOFF NEPOVIE INAK.
AK JE ROZPOR: EXPLICITNÝ ISSUE HANDOFF MÁ PREDNOSŤ, INAK PLATÍ TENTO CONTRACT.

Komunikácia: Slovensky (ak nepovieš inak).
Kód/príkazy: vždy v code blockoch.

---

## 1) Runtime a prostredie (MANDATORY)

AudioMason vždy beží vo venv `.venv`.
Keď sa uvádza venv, musí sa uviesť aktivácia aj deaktivácia:

```sh
. .venv/bin/activate
deactivate
````

---

## 2) Scope a štýl práce (STRICT)

* Implementovať iba to, čo je explicitne požadované v handoffe.
* ❌ Žiadne refaktory mimo nutného zásahu.
* ❌ Žiadne “bonus” zmeny.
* ❌ Žiadne manuálne edit kroky typu “otvor súbor a zmeň X”.
* ❌ Žiadne partial fixes.
* Preferuj minimum zmien, ktoré spĺňajú acceptance criteria.

---

## 3) AUTHORITATIVE FILE RULE (FAIL FAST)

* Ak používateľ vloží alebo uploadne súbor/snippet, je AUTHORITATIVE (má prednosť pred repo stavom).
* Ak správne riešenie závisí na súbore, ktorý nebol poskytnutý:

  * **FAIL FAST** a vyžiadať si ho
  * **nehádať / nevymýšľať** kód

---

## 4) Patchovanie (NEVYJEDNÁVATEĽNÉ)

### 4.1 Povolený formát

* ❌ NO diff patches
* ❌ NO heredoc pre patch kód
* ❌ NO inline manuálne edit pokyny
* ✅ IBA deterministický Python patch skript:
  `tools/patches/issue_<N>.py`

### 4.2 Patch skript MUST

* anchor checks (overiť kontext pred editom)
* idempotency (bezpečné opakované spustenie)
* fail-fast s jasnou chybou
* post-edit assertions (overiť, že zmena existuje)

### 4.3 Jeden issue = jeden patch skript

* Presne 1 skript: `tools/patches/issue_<N>.py`

### 4.4 Distribúcia patchov

* Patch skripty sa majú dodávať ako DOWNLOAD.
* Ak download nie je dostupný v danom prostredí:

  * patch sa poskytne v chate iba na výslovnú žiadosť používateľa.

### 4.5 Po úspechu

* Po úspešnom patchnutí a úspešných testoch sa patch skript MUSÍ zmazať:
  `rm tools/patches/issue_<N>.py`

---

## 5) Testy a git bezpečnosť (INVARIANT)

### 5.1 Invariant

* Žiadny `git add`, `git commit` ani `git push` NESMIE prebehnúť, pokiaľ neprešli testy.
* Pred KAŽDÝM `git push` musí byť `python -m pytest -q &&` v tej istej reťazi.

### 5.2 Kanonická sekvencia (POVINNÁ)

(Všetko vždy v jednom code blocku.)

```sh
python tools/patches/issue_<N>.py \
rm tools/patches/issue_<N>.py  \
python -m pytest -q && \
git add -A && \
git commit -m "<message>" && \
python -m pytest -q && \
git push
```

---

## 6) GitHub issues (STRICT)

### 6.1 Issue opening

* Otváranie issue výhradne cez `gh`.
* Pre dlhé body preferuj:
  `gh issue create/edit -F - <<'EOF' ... EOF`
  (Toto je výnimka: heredoc je zakázaný pre PATCH kód, nie pre gh body.)

### 6.2 Issue closing

* ❌ Nikdy nezatvárať issue automaticky.
* ❌ Nikdy nezatvárať issue v patch skripte.
* Po push: ZASTAVIŤ a čakať na explicitné schválenie používateľa.
* Closing comment MUSÍ obsahovať commit SHA(s) + subject(y).

### 6.3 Povinný helper na closing (template)

Keď je user pripravený zatvárať, pripraviť blok:

```sh
cd /home/pi/apps/audiomason && \
. .venv/bin/activate && \
git log --oneline -10 && \
echo && \
echo "Skopiruj sem SHA(cka) z hore uvedeneho logu, ktore patria k #<ISSUE>, potom spusti tento prikaz:" && \
echo && \
echo "gh issue close <ISSUE> -R michalholes/audiomason -c \"Resolved: <short summary>.\n\nCommits:\n- <SHA1> <subject>\n- <SHA2> <subject>\"" && \
deactivate
```

---

## 7) Release / version bump safety (CHECKLIST)

Ak sa mení verzia alebo `pyproject.toml`, po zmene vždy spraviť dev reinstall:

```sh
. .venv/bin/activate
pip uninstall -y audiomason
pip install -e .
deactivate
```

---

## 8) Notices (ak sa píšu)

Ak používateľ žiada “published notices”:

* písať po anglicky
* používať straight apostrophes
* dávať do code blocku

---

## 9) Očakávaný postup v chate

1. Potvrdiť handoff/contract (slovensky).
2. Zoznam potrebných authoritative súborov; ak chýbajú → FAIL FAST.
3. Dodať patch ako download (ak možné).
4. Dodať jeden code block s kanonickou sekvenciou.
5. Po push STOP (issue nezatvárať).

```


