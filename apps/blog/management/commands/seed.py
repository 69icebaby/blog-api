
import random
import time
from typing import Any

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from faker import Faker

from apps.auths.models import User
from apps.blog.models import Category, Tag, Post, Comment

SEED_PASSWORD = "secure-default_password123"

DEFAULT_USERS = 20
DEFAULT_POSTS = 100
DEFAULT_COMMENTS = 500

CATEGORIES_LIST = [
    "Python",
    "Django",
    "DevOps",
    "Frontend",
    "Databases",
    "Security",
    "Architecture",
    "AI & ML",
]

TAGS_LIST = [
    "async", "orm", "pytest", "docker", "kubernetes",
    "rest", "graphql", "celery", "redis", "postgresql",
    "git", "linux", "ci-cd", "react", "vue", "testing",
    "performance", "security", "websockets", "microservices",
]


class Command(BaseCommand):
    help = "Fill the database with fake data."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--users",
            type=int,
            default=DEFAULT_USERS,
            help="Number of users to create",
        )
        parser.add_argument(
            "--posts",
            type=int,
            default=DEFAULT_POSTS,
            help="Number of posts to create",
        )
        parser.add_argument(
            "--comments",
            type=int,
            default=DEFAULT_COMMENTS,
            help="Number of comments to create",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing data before seeding",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        start_time = time.time()

        users_count = options["users"]
        posts_count = options["posts"]
        comments_count = options["comments"]
        clear = options["clear"]

        # Check arguments
        if users_count < 0 or posts_count < 0 or comments_count < 0:
            raise CommandError("Argument values cannot be negative.")

        # Clear old data
        if clear:
            self.stdout.write("Clearing existing data...")

            Comment.objects.all().delete()
            Post.objects.all().delete()
            Tag.objects.all().delete()
            Category.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()

        fake = Faker()

        # Create users
        existing_emails = set(
            User.objects.values_list("email", flat=True)
        )

        users_to_create = []
        hashed_password = make_password(SEED_PASSWORD)

        while len(users_to_create) < users_count:
            first_name = fake.first_name()
            last_name = fake.last_name()

            email = (
                f"{first_name.lower()}.{last_name.lower()}"
                f"{random.randint(10, 99)}@example.com"
            )

            if email in existing_emails:
                continue

            existing_emails.add(email)

            is_active = random.choice([True, True, True, False])
            is_staff = random.random() < 0.1

            users_to_create.append(
                User(
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    password=hashed_password,
                    is_active=is_active,
                    is_staff=is_staff,
                )
            )

        if users_to_create:
            User.objects.bulk_create(users_to_create)

        created_users_count = len(users_to_create)

        # Check users
        all_users = list(User.objects.all())

        if (posts_count > 0 or comments_count > 0) and not all_users:
            raise CommandError(
                "Cannot create posts or comments without users."
            )

        # Create categories
        created_categories_count = 0

        for cat_name in CATEGORIES_LIST:
            cat_slug = slugify(cat_name)

            _, created = Category.objects.get_or_create(
                slug=cat_slug,
                defaults={"name": cat_name},
            )

            if created:
                created_categories_count += 1

        # Create tags
        created_tags_count = 0

        for tag_name in TAGS_LIST:
            tag_slug = slugify(tag_name)

            _, created = Tag.objects.get_or_create(
                slug=tag_slug,
                defaults={"name": tag_name},
            )

            if created:
                created_tags_count += 1

        all_categories = list(Category.objects.all())
        all_tags = list(Tag.objects.all())

        # Create posts
        posts_to_create = []

        used_slugs = set(
            Post.objects.values_list("slug", flat=True)
        )

        for _ in range(posts_count):
            title = fake.sentence(nb_words=6).rstrip(".")
            base_slug = slugify(title)
            slug = base_slug
            counter = 2

            while slug in used_slugs:
                slug = f"{base_slug}-{counter}"
                counter += 1

            used_slugs.add(slug)

            status = (
                "published"
                if random.random() < 0.7
                else "draft"
            )

            author = random.choice(all_users)

            category = (
                None
                if random.random() < 0.1
                else random.choice(all_categories)
            )

            body = "\n\n".join(fake.paragraphs(nb=3))

            posts_to_create.append(
                Post(
                    title=title,
                    slug=slug,
                    status=status,
                    author=author,
                    category=category,
                    body=body,
                )
            )

        created_posts = Post.objects.bulk_create(posts_to_create)

        # Add random tags to posts
        for post in created_posts:
            if all_tags:
                random_tags = random.sample(
                    all_tags,
                    k=random.randint(0, min(5, len(all_tags))),
                )
                post.tags.set(random_tags)

        # Get published posts
        published_posts = list(
            Post.objects.filter(status="published")
        )

        if comments_count > 0 and not published_posts:
            raise CommandError(
                "Cannot create comments without published posts."
            )

        # Create comments
        comments_to_create = []

        for _ in range(comments_count):
            post = random.choice(published_posts)
            author = random.choice(all_users)
            body = fake.paragraph(nb_sentences=3)

            comments_to_create.append(
                Comment(
                    post=post,
                    author=author,
                    body=body,
                )
            )

        if comments_to_create:
            Comment.objects.bulk_create(comments_to_create)

        # Print summary
        elapsed_time = time.time() - start_time

        self.stdout.write(
            f"Users: {created_users_count:5d} created"
        )
        self.stdout.write(
            f"Categories: {created_categories_count:5d} created"
        )
        self.stdout.write(
            f"Tags: {created_tags_count:5d} created"
        )
        self.stdout.write(
            f"Posts: {len(created_posts):5d} created"
        )
        self.stdout.write(
            f"Comments: {len(comments_to_create):5d} created"
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done in {elapsed_time:.2f} seconds."
            )
        )

            
