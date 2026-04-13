from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.text import slugify

from common.models import BaseModel


class Label(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="label",
        blank=True,
        null=True,
    )

    label_name = models.CharField(max_length=150, verbose_name="Nombre del Label")
    portal_web = models.URLField(max_length=255, blank=True, verbose_name="Sitio Web")
    slug = models.SlugField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Label"
        verbose_name_plural = "Labels"
        constraints = [
            models.UniqueConstraint(
                fields=["slug"],
                name="unique_label_slug",
                condition=~Q(slug=""),
            )
        ]

    def __str__(self):
        return self.label_name

    def save(self, *args, **kwargs):
        if self.slug:
            slug = slugify(self.label_name)
            same_slug = Label.objects.filter(slug=slug).exclude(uuid=self.uuid).count()
            if same_slug > 0:
                slug = f"{slug}{same_slug + 1}"
            self.slug = slug
        super().save(*args, **kwargs)

