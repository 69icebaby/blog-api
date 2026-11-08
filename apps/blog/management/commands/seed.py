from __future__ import annotations

import random
import time
from typing import Any

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.utils.text import slugify
from faker import Faker

from apps.auths.models import User
from apps.blog.models import Category, Comment, Post, Tag

SEED_PASSWORD = "BlogSeedPassword2026!"
DEFAULT_USERS = 20
DEFAULT_POSTS = 100
DEFAULT_COMMENTS = 500
INACTIVE_USER_RATE = 0.15
STAFF_USER_RATE = 0.1
PUBLISHED_POST_RATE = 0.7
UNCATEGORIZED_POST_RATE = 0.1
MAX_POST_TAGS = 5
MIN_COUNT = 0
SLUG_SUFFIX_STEP = 1
MIN_POST_TAGS = 0
POST_TITLE_WORD_COUNT = 6
POST_TITLE_MAX_LENGTH = 200
BODY_PARAGRAPH_COUNT = 3
MIN_EMAIL_SUFFIX = 10
MAX_EMAIL_SUFFIX = 9999
FIRST_POST_INDEX = 0
FIRST_SLUG_SUFFIX = 2
MIN_COMMENT_SENTENCES = 1
MAX_COMMENT_SENTENCES = 3
CATEGORIES = (
    "Python",
    "Django",
    "DevOps",
    "Frontend",
    "Databases",
    "Security",
    "Architecture",
    "AI and ML",
)
TAGS = (
    "async",
    "orm",
    "pytest",
    "docker",
    "kubernetes",
    "rest",
    "graphql",
    "celery",
    "redis",
    "postgresql",
    "git",
    "linux",
    "ci-cd",
    "react",
    "vue",
    "testing",
    "performance",
    "security",
    "websockets",
    "microservices",
)


class Command(BaseCommand):
    help = "Fill the database with fake data."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--users", type=int, default=DEFAULT_USERS, help="Number of users to create"
        )
        parser.add_argument(
            "--posts", type=int, default=DEFAULT_POSTS, help="Number of posts to create"
        )
        parser.add_argument(
            "--comments",
            type=int,
            default=DEFAULT_COMMENTS,
            help="Number of comments to create",
        )
        parser.add_argument(
            "--clear", action="store_true", help="Delete existing data before seeding"
        )

    def handle(self, *args: Any, **options: Any) -> None:
        started = time.perf_counter()
        users_count = options["users"]
        posts_count = options["posts"]
        comments_count = options["comments"]
        clear = options["clear"]
        if min(users_count, posts_count, comments_count) < MIN_COUNT:
            raise CommandError("User, post, and comment counts cannot be negative.")
        has_users = (
            User.objects.filter(is_superuser=True).exists()
            if clear
            else User.objects.exists()
        )
        if (posts_count or comments_count) and not users_count and not has_users:
            raise CommandError(
                "Posts and comments require at least one user. Increase --users."
            )
        has_published_posts = (
            Post.objects.filter(status=Post.Status.PUBLISHED).exists() and not clear
        )
        if comments_count and not posts_count and not has_published_posts:
            raise CommandError(
                "Comments were requested, but there are no published posts. Increase --posts."
            )

        if clear:
            Comment.objects.all().delete()
            Post.objects.all().delete()
            Tag.objects.all().delete()
            Category.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()

        fake = Faker()
        used_emails = set(User.objects.values_list("email", flat=True))
        hashed_password = make_password(SEED_PASSWORD)
        users = []
        while len(users) < users_count:
            first_name = fake.first_name()
            last_name = fake.last_name()
            email = f"{slugify(first_name)}.{slugify(last_name)}{random.randint(MIN_EMAIL_SUFFIX, MAX_EMAIL_SUFFIX)}@example.com"
            if email in used_emails:
                continue
            used_emails.add(email)
            users.append(
                User(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password=hashed_password,
                    is_active=random.random() >= INACTIVE_USER_RATE,
                    is_staff=random.random() < STAFF_USER_RATE,
                )
            )
        User.objects.bulk_create(users)
        all_users = list(User.objects.all())

        existing_category_slugs = set(Category.objects.values_list("slug", flat=True))
        existing_category_names = set(Category.objects.values_list("name", flat=True))
        categories = []
        for name in CATEGORIES:
            slug = slugify(name)
            if (
                name not in existing_category_names
                and slug not in existing_category_slugs
            ):
                categories.append(Category(name=name, slug=slug))
                existing_category_slugs.add(slug)
        Category.objects.bulk_create(categories)

        existing_tag_slugs = set(Tag.objects.values_list("slug", flat=True))
        existing_tag_names = set(Tag.objects.values_list("name", flat=True))
        tags = []
        for name in TAGS:
            slug = slugify(name)
            if name not in existing_tag_names and slug not in existing_tag_slugs:
                tags.append(Tag(name=name, slug=slug))
                existing_tag_slugs.add(slug)
        Tag.objects.bulk_create(tags)
        all_categories = list(Category.objects.all())
        all_tags = list(Tag.objects.all())

        used_slugs = set(Post.objects.values_list("slug", flat=True))
        posts = []
        for index in range(posts_count):
            title = fake.sentence(nb_words=POST_TITLE_WORD_COUNT).rstrip(".")[
                :POST_TITLE_MAX_LENGTH
            ]
            base_slug = slugify(title) or "post"
            slug = base_slug
            suffix = FIRST_SLUG_SUFFIX
            while slug in used_slugs:
                slug = f"{base_slug}-{suffix}"
                suffix += SLUG_SUFFIX_STEP
            used_slugs.add(slug)
            is_published = (
                index == FIRST_POST_INDEX
                and comments_count > 0
                or random.random() < PUBLISHED_POST_RATE
            )
            posts.append(
                Post(
                    author=random.choice(all_users),
                    title=title,
                    slug=slug,
                    body="\n\n".join(fake.paragraphs(nb=BODY_PARAGRAPH_COUNT)),
                    category=None
                    if random.random() < UNCATEGORIZED_POST_RATE
                    else random.choice(all_categories),
                    status=Post.Status.PUBLISHED if is_published else Post.Status.DRAFT,
                )
            )
        created_posts = Post.objects.bulk_create(posts)
        for post in created_posts:
            selected_tags = random.sample(
                all_tags,
                k=random.randint(MIN_POST_TAGS, min(MAX_POST_TAGS, len(all_tags))),
            )
            post.tags.set(selected_tags)

        published_posts = list(Post.objects.filter(status=Post.Status.PUBLISHED))
        if comments_count and not published_posts:
            raise CommandError(
                "Comments were requested, but there are no published posts. Increase --posts."
            )
        comments = [
            Comment(
                post=random.choice(published_posts),
                author=random.choice(all_users),
                body=" ".join(
                    fake.sentences(
                        nb=random.randint(MIN_COMMENT_SENTENCES, MAX_COMMENT_SENTENCES)
                    )
                ),
            )
            for _ in range(comments_count)
        ]
        Comment.objects.bulk_create(comments)

        elapsed = time.perf_counter() - started
        self.stdout.write(f"Users:      {len(users):5d} created")
        self.stdout.write(f"Categories: {len(categories):5d} created")
        self.stdout.write(f"Tags:       {len(tags):5d} created")
        self.stdout.write(f"Posts:      {len(created_posts):5d} created")
        self.stdout.write(f"Comments:   {len(comments):5d} created")
        self.stdout.write(self.style.SUCCESS(f"Done in {elapsed:.2f} seconds"))
