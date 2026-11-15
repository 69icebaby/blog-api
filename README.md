# Blog API — Homework 3

## Seed data

Install dependencies and create the schema, then seed the database:

```powershell
python manage.py migrate
python manage.py seed
```

The seed command creates sample users, categories, tags, posts and comments. Use `--users`, `--posts` and `--comments` to choose counts, or `--clear` to replace generated content while keeping superusers:

```powershell
python manage.py seed --users 50 --posts 300 --comments 1500
python manage.py seed --clear
```

## ORM query examples

Run the read-only query examples with:

```powershell
python manage.py queries
```

Run one query by number, including a data-changing query, with `--number`. Add `--sql` to display the SQL Django executed:

```powershell
python manage.py queries --number 31
python manage.py queries --number 6 --sql
```

Example output:

```text
#6 has_drafts — 1 SQL query
  True
```

Queries 40–44 change data, so the default command skips them. Run those individually with `--number`; reseed with `python manage.py seed --clear` to restore sample data.


## Admin

The admin panel uses Django Unfold. Create a superuser and start the development server with:

```powershell
python manage.py createsuperuser
python manage.py runserver
```

Posts include status tabs, filters, row actions, inline comments and a rich text body editor. The dashboard shows totals, posts by category, top authors and the published/draft share.

Screenshots for submission belong in `docs/screenshots/`: `dashboard.png`, `post-list.png`, `post-edit.png` and `user-list.png`.
