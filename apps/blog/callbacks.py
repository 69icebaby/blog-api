from decouple import config
from django.db.models import Count
from django.urls import reverse

from apps.auths.models import User
from apps.blog.models import Category, Comment, Post


def environment_callback(request):
    environment = config("BLOG_ENV_ID", default="local").lower()
    if environment == "production":
        return ["Production", "danger"]
    return ["Local", "warning"]


def drafts_badge(request):
    return Post.objects.filter(status=Post.Status.DRAFT).count()


def superuser_only(request):
    return request.user.is_superuser


def post_tabs(request):
    changelist = reverse("admin:blog_post_changelist")
    return [
        {
            "models": ["blog.post"],
            "items": [
                {"title": "All", "link": changelist},
                {"title": "Published", "link": f"{changelist}?status__exact=published"},
                {"title": "Drafts", "link": f"{changelist}?status__exact=draft"},
            ],
        }
    ]


def dashboard_callback(request, context):
    categories = Category.objects.annotate(post_total=Count("posts")).order_by("name")
    authors = User.objects.annotate(post_total=Count("posts")).order_by(
        "-post_total", "email"
    )
    published = Post.objects.filter(status=Post.Status.PUBLISHED).count()
    drafts = Post.objects.filter(status=Post.Status.DRAFT).count()
    total_posts = published + drafts
    context.update(
        {
            "dashboard_totals": {
                "users": User.objects.count(),
                "published": published,
                "drafts": drafts,
                "comments": Comment.objects.count(),
            },
            "category_chart": list(categories.values("name", "post_total")),
            "top_authors": list(
                authors.values("first_name", "last_name", "email", "post_total")[:5]
            ),
            "published_percent": round(published * 100 / total_posts)
            if total_posts
            else 0,
            "draft_percent": round(drafts * 100 / total_posts) if total_posts else 0,
        }
    )
    return context
