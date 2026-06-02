# ADR 0001: Wybór stacka technologicznego

- **Status:** Zaakceptowany
- **Data:** 2026-06-02
- **Decydent:** Michał Broniszewski

## Kontekst

Budujemy od zera webową aplikację do zarządzania amatorską ligą siatkówki:
zespoły + składy, terminarz i wyniki meczów, automatycznie generowana tabela ligi,
interfejs graficzny dla użytkownika.

Ograniczenia i preferencje:

- **Profil dewelopera:** średnio-zaawansowany, pierwsza pełna aplikacja webowa
  z deploymentem na produkcję.
- **Cel:** nauka — projekt ma być narzędziem do nauczenia się pełnego cyklu
  budowy aplikacji (modelowanie domeny, testy, CI/CD, deployment, monitoring).
- **Czas:** 2–5 h tygodniowo, MVP w 2–3 miesiące.
- **Preferencja:** backend-heavy z prostym UI — dużo logiki domeny, mało CSS-a.
- **Zasięg:** najpierw lokalnie, potem ewentualnie publiczny internet.

## Rozważane opcje

### Backend

1. **Django + DRF** — „batteries included", wbudowany admin (gotowy CRUD), ORM, migracje, auth.
2. **FastAPI + SQLAlchemy** — nowocześniejsze, async, auto-OpenAPI, ale wymaga ręcznego pisania panelu admina.
3. **Node.js + NestJS** — TypeScript end-to-end, ale stroma krzywa i większy boilerplate.
4. **Supabase / Firebase (BaaS)** — najszybciej do MVP, ale najmniej nauki „od zera".

### Frontend / UI

1. **Django Templates + HTMX + Tailwind (CDN)** — server-side rendering, interaktywność bez frameworka JS, zero build-stepa.
2. **React + Vite + TypeScript** — najpopularniejsze SPA, ale dwie aplikacje równolegle.
3. **Next.js** — full-stack w jednym frameworku, świetne SEO, ale więcej konceptów na start.
4. **Sam Django Admin** — najszybsze, ale brak UI dla widza/kibica.

### Baza danych

1. **SQLite (dev/test) → PostgreSQL (prod)** — najprostszy start, dojrzała baza w produkcji.
2. Sam PostgreSQL od początku — wymaga Dockera od dnia 1.
3. MongoDB — odpada, dane są mocno relacyjne (mecze ↔ zespoły ↔ zawodnicy).

## Decyzja

| Warstwa | Wybór |
|---|---|
| Backend | **Django 5 + Django REST Framework** |
| Panel admina | **Django Admin** (gotowy CRUD na wszystkie modele) |
| UI widza | **Django Templates + HTMX + Tailwind przez CDN** |
| Baza dev/test | **SQLite** (jeden plik, zero konfiguracji) |
| Baza prod | **PostgreSQL** (przez `docker-compose` lokalnie, managed w chmurze) |
| Pakowanie | **uv** (szybki menedżer pakietów Pythona) |
| Testy backend | **pytest + pytest-django + factory-boy** |
| Testy E2E | **Playwright (Python)** — wejdą w Etapie 4 |
| Lint/format | **ruff** (zastępuje black/isort/flake8) |
| Typowanie | **mypy** + `django-stubs` + `djangorestframework-stubs` (tryb strict) |
| Pre-commit | **pre-commit** z ruff i mypy |
| CI | **GitHub Actions** (lint + typecheck + test na każdy PR) |
| Konteneryzacja | **Docker + docker-compose** od Etapu 6 |
| Hosting (gdy gotowy) | **Railway** lub **Render** + managed Postgres |
| Monitoring (prod) | **Sentry** + **UptimeRobot** |

## Konsekwencje

### Pozytywne

- Django Admin oszczędza tygodnie pracy nad panelem CRUD — zgodne z preferencją „backend-heavy + prosty UI".
- Jeden język (Python) na backend, testy E2E i skrypty admina — mniej kontekstu do utrzymywania.
- HTMX pozwala dodać interaktywność bez wchodzenia w ekosystem JS (build, transpilacja, bundler).
- SQLite na dev = `git clone && make install && make dev` działa od razu, bez Dockera.
- Tailwind przez CDN = brak nodejs/build-stepa na start.

### Negatywne / kompromisy

- Django jest „magiczny" — niektóre mechanizmy (np. ORM, formularze) wymagają nauki konwencji zamiast czystego API.
- Brak nauki nowoczesnego frontu (React/Next) — świadomy kompromis na rzecz szybszego MVP.
- HTMX ma mniejszą społeczność niż React — mniej tutoriali do bardziej złożonych UI.
- W przyszłości przejście na SPA będzie wymagało zbudowania osobnego API (DRF już jest w zależnościach, więc droga jest otwarta).

### Drzwi otwarte na przyszłość

- DRF od początku w zależnościach → łatwe dodanie REST API kiedy zechcemy frontend SPA / mobilkę.
- Settings rozbite na `base/dev/prod` → łatwa zmiana bazy SQLite ↔ Postgres bez ruszania kodu.
- Docker + Postgres wejdą w Etapie 6 → projekt nie zostanie „uwięziony" w SQLite.
