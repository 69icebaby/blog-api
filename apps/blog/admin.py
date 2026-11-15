from typing import ClassVar

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserChangeForm as DjangoUserChangeForm
from django.contrib.auth.forms import UserCreationForm as DjangoUserCreationForm
from django.contrib.auth.models import Group
from django.db import models
from django.db.models import Count
from django.http import HttpResponseRedirect
from django.urls import reverse
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import (
    AutocompleteSelectFilter,
    BooleanRadioFilter,
    ChoicesDropdownFilter,
    MultipleRelatedDropdownFilter,
    RangeDateTimeFilter,
    RelatedDropdownFilter,
)
from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.decorators import action, display
from unfold.sections import TableSection

from .models import Category, Comment, Post, Tag

User = get_user_model()


class RelatedPostsSection(TableSection):
    verbose_name = "Posts in this category"
    related_name = "posts"
    fields: ClassVar[list[str]] = ["title", "status", "author", "created_at"]


class PostCommentsSection(TableSection):
    verbose_name = "Comments"
    related_name = "comments"
    fields: ClassVar[list[str]] = ["author", "body", "created_at"]


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ("name", "slug", "posts_count")
    search_fields = ("name", "slug")
    prepopulated_fields: ClassVar[dict] = {"slug": ("name",)}
    list_sections: ClassVar[list] = [RelatedPostsSection]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_posts_count=Count("posts"))

    @display(description="Posts", ordering="_posts_count")
    def posts_count(self, obj):
        return obj._posts_count


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ("name", "slug", "posts_count")
    search_fields = ("name", "slug")
    prepopulated_fields: ClassVar[dict] = {"slug": ("name",)}

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(_posts_count=Count("posts", distinct=True))
        )

    @display(description="Posts", ordering="_posts_count")
    def posts_count(self, obj):
        return obj._posts_count


class CommentInline(TabularInline):
    model = Comment
    fields = ("author", "body", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("author",)
    extra = 0
    per_page = 10
    tab = True
    verbose_name = "Comment"
    verbose_name_plural = "Comments"


@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    list_display = ("post_title", "author", "body_preview", "created_at")
    list_filter = (
        ("post", AutocompleteSelectFilter),
        ("author", AutocompleteSelectFilter),
        ("created_at", RangeDateTimeFilter),
    )
    list_filter_submit = True
    search_fields = ("body", "author__email", "post__title")
    autocomplete_fields = ("post", "author")
    list_select_related = ("post", "author")
    date_hierarchy = "created_at"
    BODY_PREVIEW_LENGTH: ClassVar[int] = 60

    @display(description="Post", ordering="post__title")
    def post_title(self, obj):
        return obj.post.title

    @display(description="Comment")
    def body_preview(self, obj):
        if len(obj.body) > self.BODY_PREVIEW_LENGTH:
            return f"{obj.body[: self.BODY_PREVIEW_LENGTH]}..."
        return obj.body


class UserCreationForm(DjangoUserCreationForm):
    class Meta(DjangoUserCreationForm.Meta):
        model = User
        fields = ("email", "first_name", "last_name")


class UserChangeForm(DjangoUserChangeForm):
    class Meta(DjangoUserChangeForm.Meta):
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(DjangoUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    ordering = ("email",)
    list_display = ("user_header", "active_label", "staff_label", "posts_count")
    list_filter = (("is_active", BooleanRadioFilter), ("is_staff", BooleanRadioFilter))
    search_fields = ("email", "first_name", "last_name")
    fieldsets = (
        (
            "Personal info",
            {"fields": ("email", "first_name", "last_name"), "classes": ("tab",)},
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
                "classes": ("tab",),
            },
        ),
        (
            "Important dates",
            {"fields": ("last_login", "date_joined"), "classes": ("tab",)},
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
    readonly_fields = ("last_login", "date_joined")
    filter_horizontal = ("groups", "user_permissions")
    actions = ("activate_users", "deactivate_users")

    @display(description="User", header=True)
    def user_header(self, obj):
        full_name = f"{obj.first_name} {obj.last_name}".strip() or obj.email
        initials = "".join(part[0] for part in full_name.split()[:2]).upper()
        return full_name, obj.email, initials

    @display(description="Active", label={True: "success", False: "danger"})
    def active_label(self, obj):
        return obj.is_active, "Active" if obj.is_active else "Inactive"

    @display(description="Staff", label={True: "info", False: "warning"})
    def staff_label(self, obj):
        return obj.is_staff, "Staff" if obj.is_staff else "User"

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_posts_count=Count("posts"))

    @display(description="Posts", ordering="_posts_count")
    def posts_count(self, obj):
        return obj._posts_count

    @admin.action(description="Activate selected users")
    def activate_users(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="Deactivate selected users")
    def deactivate_users(self, request, queryset):
        queryset.update(is_active=False)


class PublishActionMixin:
    @admin.action(description="Publish selected posts")
    def publish_selected(self, request, queryset):
        queryset.update(status=Post.Status.PUBLISHED)

    @admin.action(description="Move selected posts to drafts")
    def draft_selected(self, request, queryset):
        queryset.update(status=Post.Status.DRAFT)

    @action(
        description="Publish all drafts",
        url_path="publish-all-drafts",
        permissions=["change"],
    )
    def publish_all_drafts(self, request):
        Post.objects.filter(status=Post.Status.DRAFT).update(
            status=Post.Status.PUBLISHED
        )
        return HttpResponseRedirect(reverse("admin:blog_post_changelist"))

    def has_publish_all_drafts_permission(self, request):
        return request.user.has_perm("blog.change_post")

    @action(
        description="Publish / unpublish",
        url_path="toggle-publish",
        permissions=["change"],
    )
    def toggle_publish(self, request, object_id):
        post = Post.objects.get(pk=object_id)
        post.status = (
            Post.Status.DRAFT
            if post.status == Post.Status.PUBLISHED
            else Post.Status.PUBLISHED
        )
        post.save(update_fields=("status", "updated_at"))
        return HttpResponseRedirect(reverse("admin:blog_post_changelist"))

    def has_toggle_publish_permission(self, request, object_id=None):
        return request.user.has_perm("blog.change_post")

    @action(
        description="Open this post's comments",
        url_path="open-comments",
        permissions=["view"],
    )
    def open_comments(self, request, object_id):
        comments_url = reverse("admin:blog_comment_changelist")
        return HttpResponseRedirect(f"{comments_url}?post__id__exact={object_id}")

    def has_open_comments_permission(self, request, object_id=None):
        return request.user.has_perm("blog.view_comment")

    @action(description="Save & publish", permissions=["change"])
    def save_and_publish(self, request, obj):
        obj.status = Post.Status.PUBLISHED
        obj.save(update_fields=("status", "updated_at"))
        return HttpResponseRedirect(reverse("admin:blog_post_change", args=(obj.pk,)))

    def has_save_and_publish_permission(self, request, object_id=None):
        return request.user.has_perm("blog.change_post")


@admin.register(Post)
class PostAdmin(PublishActionMixin, ModelAdmin):
    list_display = (
        "post_header",
        "status_label",
        "category",
        "tags_dropdown",
        "comments_count",
        "created_at",
    )
    list_filter = (
        ("status", ChoicesDropdownFilter),
        ("category", RelatedDropdownFilter),
        ("tags", MultipleRelatedDropdownFilter),
        ("author", AutocompleteSelectFilter),
        ("created_at", RangeDateTimeFilter),
    )
    list_filter_submit = True
    search_fields = ("title", "body", "author__email")
    autocomplete_fields = ("author", "category", "tags")
    prepopulated_fields: ClassVar[dict] = {"slug": ("title",)}
    list_select_related = ("author", "category")
    list_sections: ClassVar[list] = [PostCommentsSection]
    list_per_page = 20
    actions = ("publish_selected", "draft_selected")
    actions_row: ClassVar[list[str]] = ["toggle_publish"]
    actions_list: ClassVar[list[str]] = ["publish_all_drafts"]
    actions_detail: ClassVar[list[str]] = ["open_comments"]
    actions_submit_line: ClassVar[list[str]] = ["save_and_publish"]
    inlines = (CommentInline,)
    warn_unsaved_form = True
    formfield_overrides: ClassVar[dict] = {models.TextField: {"widget": WysiwygWidget}}
    fieldsets = (
        ("Content", {"fields": ("title", "slug", "body"), "classes": ("tab",)}),
        (
            "Classification",
            {"fields": ("category", "tags", "status"), "classes": ("tab",)},
        ),
        (
            "Meta",
            {"fields": ("author", "created_at", "updated_at"), "classes": ("tab",)},
        ),
    )
    readonly_fields = ("created_at", "updated_at")

    @display(description="Post", header=True, ordering="title")
    def post_header(self, obj):
        initials = "".join(
            part[0]
            for part in f"{obj.author.first_name} {obj.author.last_name}".split()[:2]
        ).upper()
        return obj.title, obj.author.email, initials

    @display(
        description="Status",
        label={Post.Status.PUBLISHED: "success", Post.Status.DRAFT: "warning"},
    )
    def status_label(self, obj):
        return obj.status, obj.get_status_display()

    @display(description="Tags", dropdown=True)
    def tags_dropdown(self, obj):
        tags = list(obj.tags.all())
        return {
            "title": f"{len(tags)} tags",
            "items": [{"title": tag.name} for tag in tags],
        }

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(_comments_count=Count("comments", distinct=True))
            .prefetch_related("tags")
            .select_related("author", "category")
        )

    @display(description="Comments", ordering="_comments_count")
    def comments_count(self, obj):
        return obj._comments_count

    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)


class GroupAdmin(ModelAdmin):
    search_fields = ("name",)
    filter_horizontal = ("permissions",)


try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass

admin.site.register(Group, GroupAdmin)
