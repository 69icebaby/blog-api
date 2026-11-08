# Blog API — Homework 2

## Seeding

Install the project dependencies, apply migrations, then run `python manage.py seed` to add sample users, categories, tags, posts and comments.

```powershell
python manage.py migrate
python manage.py seed
python manage.py createsuperuser
python manage.py runserver
```

The seed command accepts `--users`, `--posts` and `--comments` to change the default amounts (20, 100 and 500). Add `--clear` to remove generated content before seeding while keeping superusers.

```powershell
python manage.py seed --users 50 --posts 300 --comments 1500
python manage.py seed --clear
python manage.py seed --help
```

All sample accounts use the password stored in `SEED_PASSWORD` in `apps/blog/management/commands/seed.py`.

## Admin

The admin panel uses Django Unfold. Posts include status tabs, filters, row actions, inline comments and a rich text body editor. The dashboard shows totals, posts by category, top authors and the published/draft share.

Screenshots for submission belong in `docs/screenshots/`:

- `dashboard.png`
- `post-list.png`
- `post-edit.png`
- `user-list.png`
