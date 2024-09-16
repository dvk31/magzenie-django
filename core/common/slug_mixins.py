from django.db import models
from django.utils.text import slugify

class SlugMixin(models.Model):
    slug = models.SlugField(unique=True, blank=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.generate_unique_slug()
        super().save(*args, **kwargs)

    def generate_unique_slug(self):
        if hasattr(self, 'name'):
            slug_source = self.name
        elif hasattr(self, 'title'):
            slug_source = self.title
        else:
            raise AttributeError("The model must have either a 'name' or 'title' field.")

        slug = slugify(slug_source)
        unique_slug = slug
        num = 1
        while self.__class__.objects.filter(slug=unique_slug).exists():
            unique_slug = f"{slug}-{num}"
            num += 1
        return unique_slug