# score_system

Aplikacja do zarządzania rozgrywkami amatorskiej ligi siatkówki:
zespoły, składy, terminarz, wyniki meczów i automatycznie generowana tabela.

> **Status:** Wczesny rozwój (Etap 0 — Fundamenty).
> Pełny plan i roadmapa: [`docs/`](docs/) oraz plan w sesji Claude.

## Stack

- **Backend:** Django 5 + Django REST Framework
- **UI:** Django Templates + HTMX + Tailwind (CDN)
- **Baza:** SQLite (dev) / PostgreSQL (prod)
- **Testy:** pytest + pytest-django + Playwright (E2E)
- **Jakość:** ruff + mypy + pre-commit
- **CI:** GitHub Actions

Pełne uzasadnienie wyboru: [`docs/adr/0001-wybor-stacka.md`](docs/adr/0001-wybor-stacka.md).

## Wymagania

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) — szybki menedżer pakietów Pythona
  (instalacja: `curl -LsSf https://astral.sh/uv/install.sh | sh`)

## Quick start (lokalnie)

```bash
# 1. Klon i instalacja zależności
git clone https://github.com/michbroniszewski/score_system.git
cd score_system
make install         # uv sync + pre-commit install

# 2. Skopiuj plik z przykładowymi zmiennymi środowiskowymi
cp .env.example .env

# 3. Migracje (utworzy db.sqlite3)
make migrate

# 4. Utwórz konto admina
make superuser

# 5. Uruchom serwer deweloperski
make dev
# → http://localhost:8000
# → Panel admina: http://localhost:8000/admin
```

## Najczęściej używane komendy

```bash
make help          # lista wszystkich komend
make dev           # serwer deweloperski
make test          # testy
make test-cov      # testy z raportem pokrycia (HTML w htmlcov/)
make lint          # ruff check + format check
make format        # ruff format + auto-fix
make typecheck     # mypy
make migrate       # zastosuj migracje
make makemigrations  # wygeneruj nowe migracje
```

## Struktura projektu

```
score_system/
├── pyproject.toml              # zależności i konfiguracja narzędzi
├── Makefile                    # skróty komend
├── .pre-commit-config.yaml     # hooki uruchamiane przed commitem
├── .github/workflows/ci.yml    # CI: lint + typecheck + test
├── .env.example                # szablon zmiennych środowiskowych
├── CHANGELOG.md                # historia zmian
├── docs/adr/                   # Architecture Decision Records
├── league_app/                 # konfiguracja Django (Etap 1)
│   └── settings/{base,dev,prod}.py
├── core/                       # apka domeny (Etap 2+)
│   ├── models.py
│   ├── admin.py
│   ├── views.py
│   ├── standings.py
│   ├── templates/
│   └── tests/
└── manage.py
```

## Workflow rozwoju

1. Każda zmiana = osobny branch + Pull Request.
2. Każdy PR musi mieć test pokrywający zmianę.
3. CI (`lint` + `typecheck` + `test`) musi być zielone przed merge.
4. Commity w stylu [Conventional Commits](https://www.conventionalcommits.org/):
   `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`.
5. Każda ważna decyzja → nowy plik w `docs/adr/NNNN-tytul.md`.

## Licencja

MIT — zobacz [`LICENSE`](LICENSE).
