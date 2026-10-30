# blog/models.py - model Product: jeden post na blogu
from django.db import models
from django.utils.text import slugify


class Product(models.Model):
    name = models.CharField('Tytuł', max_length=255)
    slug = models.SlugField('Slug', max_length=255, unique=True, blank=True)
    author = models.CharField('Autor', max_length=100, blank=True)
    description = models.TextField('Treść')
    image = models.ImageField('Obrazek', upload_to='products/')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']  # najnowsze posty na górze

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # slug generujemy z tytułu tylko przy pierwszym zapisie,
        # żeby edycja tytułu nie psuła istniejących linków
        if not self.slug:
            # slugify gubi polskie ł, więc zamieniamy je ręcznie
            base = slugify(self.name.replace('ł', 'l').replace('Ł', 'L')) or 'post'
            slug = base
            n = 2
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{n}'
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def short_description(self):
        """Skrót treści do 30 słów - używany na liście postów."""
        words = self.description.split()
        if len(words) > 30:
            return ' '.join(words[:30]) + '...'
        return self.description
