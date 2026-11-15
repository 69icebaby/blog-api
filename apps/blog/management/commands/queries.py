from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.models import QuerySet
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.auths.models import User
from apps.blog.models import Category, Post, Tag
from apps.blog.queries import QUERIES

SKIP_QUERIES = {40, 41, 42, 43, 44}
RESULT_LIMIT = 5
SAMPLE_DAYS = 365
SAMPLE_TEXT = "a"
SAMPLE_SLUG = "django"
SAMPLE_SECOND_SLUG = "orm"
SAMPLE_DOMAIN = "example.com"
SAMPLE_EMAIL_FALLBACK = "seed@example.com"
SAMPLE_PAGE = 1
SAMPLE_POPULARITY = 1
QUERY_ARGUMENTS = {
    7: {"page": SAMPLE_PAGE},
    8: {"word": SAMPLE_TEXT},
    9: {"domain": SAMPLE_DOMAIN},
    13: {"days": SAMPLE_DAYS},
    14: {"start": date.min, "end": date.max},
    21: {"first_slug": SAMPLE_SECOND_SLUG, "second_slug": SAMPLE_SECOND_SLUG},
    34: {"min_posts": SAMPLE_POPULARITY},
    40: {"name": "queries sample tag"},
}


def sample_arguments(number):
    """Build representative arguments, using existing rows where needed."""
    arguments = dict(QUERY_ARGUMENTS.get(number, {}))
    if number == 4:
        slug = Post.objects.order_by("pk").values_list("slug", flat=True).first()
        return {"slug": slug or "missing"}
    if number == 7:
        return arguments
    if number in {8, 22, 37}:
        return arguments if number == 8 else {"text": SAMPLE_TEXT}
    if number == 9:
        return arguments
    if number == 11:
        slugs = list(Category.objects.order_by("pk").values_list("slug", flat=True)[:2])
        return {"slugs": slugs}
    if number == 12:
        created_at = Post.objects.order_by("created_at").values_list("created_at", flat=True).first()
        created_at = created_at or timezone.now()
        return {"year": created_at.year, "month": created_at.month}
    if number == 13 or number == 41:
        return arguments
    if number == 14:
        return arguments
    if number == 15:
        email = User.objects.filter(posts__status=Post.Status.PUBLISHED).values_list("email", flat=True).first()
        return {"email": email or SAMPLE_EMAIL_FALLBACK}
    if number == 16:
        slug = Tag.objects.order_by("pk").values_list("slug", flat=True).first()
        return {"tag_slug": slug or SAMPLE_SECOND_SLUG}
    if number == 17:
        slug = Category.objects.order_by("pk").values_list("slug", flat=True).first()
        return {"category_slug": slug or SAMPLE_SLUG}
    if number == 21:
        slugs = list(Tag.objects.order_by("pk").values_list("slug", flat=True)[:2])
        arguments.update(first_slug=slugs[0] if slugs else SAMPLE_SECOND_SLUG, second_slug=slugs[1] if len(slugs) > 1 else SAMPLE_SECOND_SLUG)
        return arguments
    if number == 34:
        return arguments
    if number == 40:
        return arguments
    if number == 42:
        category_slug = Category.objects.order_by("pk").values_list("slug", flat=True).first()
        tag_slug = Tag.objects.order_by("pk").values_list("slug", flat=True).first()
        return {"category_slug": category_slug or SAMPLE_SLUG, "tag_slug": tag_slug or SAMPLE_SECOND_SLUG}
    if number == 43:
        slugs = list(Category.objects.order_by("pk").values_list("slug", flat=True)[:2])
        return {"source_slug": slugs[0] if slugs else SAMPLE_SLUG, "target_slug": slugs[1] if len(slugs) > 1 else SAMPLE_SECOND_SLUG}
    return {}


class Command(BaseCommand):
    help = "Run the blog ORM query examples"

    def add_arguments(self, parser):
        parser.add_argument("--number", type=int, help="Run only one query (1-50)")
        parser.add_argument("--sql", action="store_true", help="Print captured SQL")

    def handle(self, *args, **options):
        number = options["number"]
        if number is not None and number not in QUERIES:
            raise CommandError(f"Query number {number} does not exist.")
        numbers = [number] if number is not None else [n for n in sorted(QUERIES) if n not in SKIP_QUERIES]
        for query_number in numbers:
            function = QUERIES[query_number]
            arguments = sample_arguments(query_number)
            with CaptureQueriesContext(connection) as context:
                result = function(**arguments)
                if isinstance(result, QuerySet):
                    rows = list(result)
                elif isinstance(result, list):
                    rows = result
                else:
                    rows = result
            self.stdout.write(f"#{query_number} {function.__name__} — {len(context.captured_queries)} SQL query")
            if options["sql"]:
                for captured in context.captured_queries:
                    self.stdout.write(captured["sql"])
            if isinstance(rows, list):
                for item in rows[:RESULT_LIMIT]:
                    self.stdout.write(f"  {self.format_item(item)}")
                self.stdout.write(f"  ({len(rows)} rows)")
            else:
                self.stdout.write(f"  {self.format_item(rows)}")

    @staticmethod
    def format_item(item):
        if hasattr(item, "_meta"):
            field_names = {field.attname for field in item._meta.concrete_fields}
            values = {name: value for name, value in item.__dict__.items() if name not in field_names and name != "_state"}
            return f"{item} {values}" if values else str(item)
        return repr(item)
