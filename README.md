# Simple Notes Application

A simple notes app where users can create, view, edit, and delete notes (title + content).

## Containers / Ports

- Frontend (React): http://localhost:3000  
- Backend (FastAPI): http://localhost:3001  
- Database: SQLite file stored at:
  `simple-notes-application-196635-196652/database/myapp.db`

## API

Backend provides:

- `GET /notes`
- `POST /notes`
- `GET /notes/{id}`
- `PUT /notes/{id}`
- `DELETE /notes/{id}`

CORS is enabled for `http://localhost:3000`.

## Persistence / Migrations

On backend startup, the `notes` table is created if it does not already exist.

Schema:
- id (INTEGER PRIMARY KEY AUTOINCREMENT)
- title (TEXT NOT NULL)
- content (TEXT NOT NULL)
- created_at (TEXT, ISO-8601 UTC)
- updated_at (TEXT, ISO-8601 UTC)

## Configuration

No external services required.
