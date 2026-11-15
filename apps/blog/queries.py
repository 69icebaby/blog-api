from datetime import date, timedelta
from typing import Any

from django.db.models import (
    Avg,
    Case,
    Count,
    Exists,
    F,
    OuterRef,
    Prefetch,
    Q,
    QuerySet,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone
from django.utils.text import slugify

from apps.auths.models import User

from .models import Category, Comment, Post, Tag

PAGE_SIZE = 10
NEWEST_POST_LIMIT = 5
RECENT_DAYS = 30
SEARCH_WORD = "the"
DEFAULT_CATEGORY_SLUGS = ("django", "python")
DEFAULT_TAG_SLUGS = ("orm", "pytest")
DEFAULT_MONTH = 11
EDIT_HOUR = 1
POPULAR_HOT_COUNT = 10
POPULAR_NORMAL_COUNT = 3
TOP_AUTHOR_LIMIT = 5
FEED_LIMIT = 50
TAG_POST_LIMIT = 20
UNCATEGORIZED = "Uncategorized"


def categories_by_name() -> QuerySet[Category]:
    """Return categories sorted by name."""
    return Category.objects.order_by("name")


def published_posts() -> QuerySet[Post]:
    """Return published posts, newest first."""
    return Post.objects.filter(status=Post.Status.PUBLISHED).order_by("-created_at")


def newest_published_posts() -> QuerySet[Post]:
    """Return the five newest published posts."""
    return published_posts()[:NEWEST_POST_LIMIT]


def post_by_slug(slug: str) -> Post | None:
    """Find a post by its slug without raising when absent."""
    return Post.objects.filter(slug=slug).first()


def active_users_count() -> int:
    """Count active non-staff users."""
    return User.objects.filter(is_active=True, is_staff=False).count()


def has_drafts() -> bool:
    """Return whether any draft exists."""
    return Post.objects.filter(status=Post.Status.DRAFT).exists()


def published_posts_page(page: int) -> QuerySet[Post]:
    """Return one page of published posts."""
    page = max(page, 1)
    return published_posts()[(page - 1) * PAGE_SIZE:page * PAGE_SIZE]


def posts_with_word_in_title(word: str) -> QuerySet[Post]:
    """Find posts whose title contains a word, case-insensitively."""
    return Post.objects.filter(title__icontains=word)


def users_with_email_domain(domain: str) -> QuerySet[User]:
    """Find users at an email domain."""
    return User.objects.filter(email__iendswith=f"@{domain}")


def posts_without_category() -> QuerySet[Post]:
    """Return posts without a category."""
    return Post.objects.filter(category__isnull=True)


def categories_by_slugs(slugs: list[str]) -> QuerySet[Category]:
    """Find categories with the requested slugs."""
    return Category.objects.filter(slug__in=slugs)


def posts_in_month(year: int, month: int) -> QuerySet[Post]:
    """Return posts created in a calendar month."""
    return Post.objects.filter(created_at__year=year, created_at__month=month)


def posts_last_days(days: int) -> QuerySet[Post]:
    """Return posts created within the last number of days."""
    return Post.objects.filter(created_at__gte=timezone.now() - timedelta(days=days))


def posts_between(start: date, end: date) -> QuerySet[Post]:
    """Return posts created on either inclusive date boundary."""
    return Post.objects.filter(created_at__date__range=(start, end))


def author_published_posts(email: str) -> QuerySet[Post]:
    """Return published posts by an email address."""
    return published_posts().filter(author__email__iexact=email)


def posts_with_tag(tag_slug: str) -> QuerySet[Post]:
    """Return posts carrying the given tag."""
    return Post.objects.filter(tags__slug=tag_slug)


def comments_in_category(category_slug: str) -> QuerySet[Comment]:
    """Return comments on posts in a category."""
    return Comment.objects.filter(post__category__slug=category_slug)


def users_with_published_posts() -> QuerySet[User]:
    """Return each user who has published a post once."""
    return User.objects.filter(posts__status=Post.Status.PUBLISHED).distinct()


def posts_without_tags() -> QuerySet[Post]:
    """Return posts with no tags."""
    return Post.objects.filter(tags__isnull=True)


def users_without_comments() -> QuerySet[User]:
    """Return users who have never commented."""
    return User.objects.filter(comments__isnull=True)


def posts_with_both_tags(first_slug: str, second_slug: str) -> QuerySet[Post]:
    """Return posts carrying both specified tags."""
    return Post.objects.filter(tags__slug=first_slug).filter(tags__slug=second_slug)


def search_posts(text: str) -> QuerySet[Post]:
    """Search post title or body without case sensitivity."""
    return Post.objects.filter(Q(title__icontains=text) | Q(body__icontains=text)).distinct()


def published_posts_missing_info() -> QuerySet[Post]:
    """Return published posts missing a category or tags."""
    return published_posts().filter(Q(category__isnull=True) | Q(tags__isnull=True)).distinct()


def edited_posts() -> QuerySet[Post]:
    """Return posts edited more than one hour after creation."""
    return Post.objects.filter(updated_at__gt=F("created_at") + timedelta(hours=EDIT_HOUR))


def comments_by_post_author() -> QuerySet[Comment]:
    """Return comments written by the post author."""
    return Comment.objects.filter(author_id=F("post__author_id"))


def comments_before_post() -> QuerySet[Comment]:
    """Return comments created before their post."""
    return Comment.objects.filter(created_at__lt=F("post__created_at"))


def published_authors_emails() -> list[str]:
    """Return unique published-author emails in order."""
    return list(User.objects.filter(posts__status=Post.Status.PUBLISHED).order_by("email").values_list("email", flat=True).distinct())


def published_posts_overview() -> list[dict[str, Any]]:
    """Return summary dictionaries for published posts."""
    return list(published_posts().values("title", author_email=F("author__email"), category_name=Case(When(category__isnull=True, then=Value(UNCATEGORIZED)), default=F("category__name"))))


def posts_stats() -> dict[str, Any]:
    """Aggregate total, status counts and date bounds in one query."""
    stats = Post.objects.aggregate(total=Count("pk"), published=Count("pk", filter=Q(status=Post.Status.PUBLISHED)), drafts=Count("pk", filter=Q(status=Post.Status.DRAFT)), first_post_at=django_min("created_at"), last_post_at=django_max("created_at"))
    return stats


def django_min(field: str) -> Any:
    from django.db.models import Min
    return Min(field)


def django_max(field: str) -> Any:
    from django.db.models import Max
    return Max(field)


def average_comments_per_post() -> float:
    """Average comment count over published posts, including zeros."""
    value = Post.objects.filter(status=Post.Status.PUBLISHED).annotate(comment_total=Count("comments")).aggregate(value=Avg("comment_total"))
    return round(value["value"] or 0.0, 2)


def categories_with_post_count() -> QuerySet[Category]:
    """Return categories annotated with their post counts."""
    return Category.objects.annotate(post_count=Count("posts")).order_by("-post_count", "name")


def categories_with_published_count() -> QuerySet[Category]:
    """Return categories with published post counts, including zeroes."""
    return Category.objects.annotate(published_count=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED)))


def top_authors() -> QuerySet[User]:
    """Return the five leading published-post authors."""
    return User.objects.annotate(published_count=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED))).order_by("-published_count", "email")[:TOP_AUTHOR_LIMIT]


def popular_tags(min_posts: int) -> QuerySet[Tag]:
    """Return tags used on at least the requested number of posts."""
    return Tag.objects.annotate(post_count=Count("posts")).filter(post_count__gte=min_posts)


def posts_per_status() -> list[dict[str, Any]]:
    """Return post totals grouped by status."""
    return list(Post.objects.values("status").annotate(count=Count("pk")).order_by("status"))


def users_activity() -> QuerySet[User]:
    """Return users with independent post and comment counts."""
    post_count = Post.objects.filter(author=OuterRef("pk")).order_by().values("author").annotate(n=Count("pk")).values("n")
    comment_count = Comment.objects.filter(author=OuterRef("pk")).order_by().values("author").annotate(n=Count("pk")).values("n")
    return User.objects.annotate(post_count=Coalesce(Subquery(post_count), 0), comment_count=Coalesce(Subquery(comment_count), 0))


def search_users_by_full_name(text: str) -> QuerySet[User]:
    """Search users by concatenated first and last names."""
    from django.db.models.functions import Concat
    return User.objects.annotate(full_name=Concat("first_name", Value(" "), "last_name")).filter(full_name__icontains=text)


def published_posts_per_month() -> list[dict[str, Any]]:
    """Return published post counts grouped by month."""
    return list(published_posts().annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("pk")).order_by("month"))


def posts_with_popularity() -> QuerySet[Post]:
    """Return posts annotated with comment count and popularity label."""
    return Post.objects.annotate(comment_count=Count("comments")).annotate(popularity=Case(When(comment_count__gte=POPULAR_HOT_COUNT, then=Value("hot")), When(comment_count__gte=POPULAR_NORMAL_COUNT, then=Value("normal")), default=Value("quiet")))


def get_or_create_tag(name: str) -> tuple[Tag, bool]:
    """Find or create a tag by its unique slug."""
    return Tag.objects.get_or_create(slug=slugify(name), defaults={"name": name})


def publish_old_drafts(days: int) -> int:
    """Publish drafts older than the given number of days."""
    cutoff = timezone.now() - timedelta(days=days)
    qs = Post.objects.filter(status=Post.Status.DRAFT, created_at__lt=cutoff)
    return qs.update(status=Post.Status.PUBLISHED, updated_at=timezone.now())


def tag_category_posts(category_slug: str, tag_slug: str) -> int:
    """Attach a tag to posts in a category and return their count."""
    posts = Post.objects.filter(category__slug=category_slug)
    count = posts.count()
    tag = Tag.objects.get(slug=tag_slug)
    through = Post._meta.get_field("tags").remote_field.through
    through.objects.bulk_create(
        [through(post_id=post_id, tag_id=tag.pk) for post_id in posts.values_list("pk", flat=True)],
        ignore_conflicts=True,
    )
    return count


def merge_categories(source_slug: str, target_slug: str) -> int:
    """Move posts to another category and delete the source."""
    source = Category.objects.get(slug=source_slug)
    target = Category.objects.get(slug=target_slug)
    count = source.posts.count()
    source.posts.update(category=target)
    source.delete()
    return count


def delete_inactive_users_comments() -> int:
    """Delete comments written by inactive users."""
    deleted, _ = Comment.objects.filter(author__is_active=False).delete()
    return deleted


def published_feed() -> list[str]:
    """Build a feed from published posts using one joined query."""
    posts = published_posts().select_related("author", "category")[:FEED_LIMIT]
    return [f"{p.title} | {p.author.email} | {p.category.name if p.category else UNCATEGORIZED}" for p in posts]


def newest_posts_with_tags() -> list[str]:
    """Build lines for the newest posts and their tags."""
    posts = Post.objects.order_by("-created_at").prefetch_related("tags")[:TAG_POST_LIMIT]
    return [f"{p.title}: {', '.join(t.name for t in p.tags.all())}" for p in posts]


def categories_with_published_posts() -> dict[str, list[str]]:
    """Map categories to their published post titles."""
    posts = Post.objects.filter(status=Post.Status.PUBLISHED).order_by("-created_at")
    categories = Category.objects.prefetch_related(Prefetch("posts", queryset=posts, to_attr="published_posts"))
    return {c.name: [p.title for p in c.published_posts] for c in categories}


def posts_with_last_comment() -> QuerySet[Post]:
    """Annotate published posts with their newest comment body."""
    latest = Comment.objects.filter(post=OuterRef("pk")).order_by("-created_at").values("body")[:1]
    return published_posts().annotate(last_comment=Subquery(latest))


def posts_with_staff_comments() -> QuerySet[Post]:
    """Return posts with at least one staff user's comment."""
    comments = Comment.objects.filter(post=OuterRef("pk"), author__is_staff=True)
    return Post.objects.filter(Exists(comments))


def users_with_draft_as_latest_post() -> QuerySet[User]:
    """Return users whose newest post is a draft, with its status."""
    latest = Post.objects.filter(author=OuterRef("pk")).order_by("-created_at", "-pk").values("status")[:1]
    return User.objects.annotate(latest_post_status=Subquery(latest)).filter(latest_post_status=Post.Status.DRAFT)


QUERIES = {
    1: categories_by_name, 2: published_posts, 3: newest_published_posts, 4: post_by_slug,
    5: active_users_count, 6: has_drafts, 7: published_posts_page, 8: posts_with_word_in_title,
    9: users_with_email_domain, 10: posts_without_category, 11: categories_by_slugs,
    12: posts_in_month, 13: posts_last_days, 14: posts_between, 15: author_published_posts,
    16: posts_with_tag, 17: comments_in_category, 18: users_with_published_posts,
    19: posts_without_tags, 20: users_without_comments, 21: posts_with_both_tags,
    22: search_posts, 23: published_posts_missing_info, 24: edited_posts,
    25: comments_by_post_author, 26: comments_before_post, 27: published_authors_emails,
    28: published_posts_overview, 29: posts_stats, 30: average_comments_per_post,
    31: categories_with_post_count, 32: categories_with_published_count, 33: top_authors,
    34: popular_tags, 35: posts_per_status, 36: users_activity, 37: search_users_by_full_name,
    38: published_posts_per_month, 39: posts_with_popularity, 40: get_or_create_tag,
    41: publish_old_drafts, 42: tag_category_posts, 43: merge_categories,
    44: delete_inactive_users_comments, 45: published_feed, 46: newest_posts_with_tags,
    47: categories_with_published_posts, 48: posts_with_last_comment,
    49: posts_with_staff_comments, 50: users_with_draft_as_latest_post,
}
