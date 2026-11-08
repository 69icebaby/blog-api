from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def assign_existing_posts(apps, schema_editor):
    Post = apps.get_model("blog", "Post")
    User = apps.get_model("auths", "User")
    database = schema_editor.connection.alias
    posts = Post.objects.using(database).filter(author__isnull=True)
    if not posts.exists():
        return
    author = User.objects.using(database).order_by("pk").first()
    if author is None:
        author = User(
            email="legacy-post-author@example.invalid",
            first_name="Legacy",
            last_name="Author",
            password="!",
            is_active=False,
            is_staff=False,
        )
        author.save(using=database)
    posts.update(author_id=author.pk)


class Migration(migrations.Migration):
    dependencies = [
        ("auths", "0002_alter_user_id"),
        ("blog", "0002_alter_category_id_alter_comment_id_alter_post_id_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="author",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name="posts", to=settings.AUTH_USER_MODEL),
        ),
        migrations.RunPython(assign_existing_posts, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="post",
            name="author",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="posts", to=settings.AUTH_USER_MODEL),
        ),
    ]
