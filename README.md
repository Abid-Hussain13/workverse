# Workverse

**Find local workers. Book them. Rate them.**

Workverse is a services marketplace built with Django: clients search for skilled workers by category and city, send booking requests, and rate the work afterwards — while workers run their own profile, availability and dashboard from the same app.

## How it works

1. **Browse** — the home page lists workers with search plus filters for category, city, availability and status; each card shows the worker's average rating and jobs completed.
2. **Book** — a client opens a worker's detail page and sends a booking request describing the job. The request moves through `pending → accepted / rejected → completed`, with an auto-complete deadline so stale jobs don't hang forever.
3. **Rate** — after completion the client leaves a 1–5 rating and a comment. Only accounts that are at least 7 days old can rate, which keeps throwaway accounts from inflating scores.
4. **Work** — anyone can become a worker: pick categories, set experience, city and availability, then manage incoming requests from the worker dashboard (accept, reject, complete) and edit the public profile.

```
Client → find workers → booking request → worker accepts → job completed → review
```

## Features

- **Two-sided accounts** — custom user model (email login, unique phone number to block fake signups, profile picture, `is_worker` flag).
- **Worker profiles** — multi-category skills, experience years, city, availability window, bio, jobs-completed counter and computed average rating.
- **Booking lifecycle** — pending / accepted / rejected / completed with timestamps and auto-completion.
- **Reviews** — rating + comment per completed booking, eligibility gated to 7-day-old accounts.
- **Built-in admin panel** — `/admin-panel/` pages for overview, users, workers and bookings, alongside stock Django admin at `/admin/`.
- **Contact forms** — support messages with issue types (general, complaints, technical), resolution tracking and admin notes.

## Stack

| Layer    | Tech                                                              |
| -------- | ----------------------------------------------------------------- |
| Backend  | Python 3.14, Django 6, Django session auth, SQLite                |
| Frontend | Django templates, Tailwind CSS (CDN), Tabler icons, Google Fonts  |
| Storage  | SQLite by default; a Supabase Postgres config is included but commented out |

The UI uses Inter / Space Grotesk / JetBrains Mono with a dark sidebar layout, toast messages and a worker-focused design system.

## Project structure

```
Workverse/
├── config/            # Django project — settings, root URLs, WSGI/ASGI
├── manage.py
├── db.sqlite3
├── profile_pics/      # uploaded profile pictures (dev)
└── myapp/
    ├── models.py      # User, City, Category, WorkerProfile, BookingRequest, Review, ContactMessage
    ├── views.py       # find_workers, bookings, auth, worker dashboard, admin panel
    ├── forms.py
    ├── urls.py
    └── templates/     # base, find_workers, worker_detail, my_bookings, dashboard, admin, auth
```

## Getting started

### Prerequisites

- Python 3.14+ (3.14.4 is what this was built on)
- Django 6 and Pillow (for profile picture uploads):

```bash
cd Workverse
python3 -m venv .venv
source .venv/bin/activate
pip install "Django>=6.0" pillow
```

### Run it

```bash
python manage.py migrate
python manage.py runserver
```

Open http://localhost:8000 — sign up, browse workers, or log into the admin panel at `/admin/`.

## Main routes

```
GET  /                        worker directory with search + filters
GET  /worker/<worker_id>/     public worker profile + reviews + booking form
GET  /bookings/               your booking requests (client view)
GET  /become-worker/          create a worker profile
GET  /worker/dashboard/       accept / reject / complete incoming requests
GET  /worker/edit/            edit your worker profile
GET  /admin-panel/overview/   built-in admin panel (users, workers, bookings)
POST /contact/                contact / support messages
```

Auth routes: `/signup/`, `/login/`, `/logout/`.

## Notes

- Ships in `DEBUG = True` with SQLite and a development `SECRET_KEY` — swap both before deploying.
- The Postgres/Supabase block in `config/settings.py` is commented out; re-enable it (with credentials supplied via environment variables, not committed to the repo) for production.
- Seed the directory with a few workers and categories to see the filters and ratings in action.
