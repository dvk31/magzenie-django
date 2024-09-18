from django.db import models
from django.conf import settings
from core.models import BaseModel

class MagazineType(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return self.name

class Template(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField()
    magazine_type = models.ForeignKey(MagazineType, on_delete=models.SET_NULL, null=True, related_name='templates')
    thumbnail_image = models.ImageField(upload_to='templates/thumbnails/')
    image = models.ImageField(upload_to='templates/images/')
    structure = models.JSONField()

    def __str__(self):
        return f"Template {self.id}: {self.name}"

class TemplateExample(BaseModel):
    template = models.ForeignKey(Template, on_delete=models.CASCADE, related_name='examples')
    example_image = models.ImageField(upload_to='templates/examples/')
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Example {self.id} for Template {self.template.name}"

class Magazine(BaseModel):
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Published', 'Published'),
        ('Archived', 'Archived'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='magazines')
    magazine_type = models.ForeignKey(MagazineType, on_delete=models.SET_NULL, null=True, related_name='magazines')
    template = models.ForeignKey(Template, on_delete=models.SET_NULL, null=True, related_name='magazines')
    title = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft')
    thumbnail = models.ImageField(upload_to='magazines/thumbnails/', null=True, blank=True)

    def __str__(self):
        return f"Magazine {self.id}: {self.title}"

    def duplicate(self):
        duplicated_magazine = Magazine.objects.create(
            user=self.user,
            magazine_type=self.magazine_type,
            template=self.template,
            title=f"{self.title} (Copy)",
            status='Draft',
            thumbnail=self.thumbnail
        )
        for page in self.pages.all():
            duplicated_page = Page.objects.create(
                magazine=duplicated_magazine,
                content=page.content,
                accepted=page.accepted
            )
            for qr in page.qrcodes.all():
                QRCode.objects.create(
                    page=duplicated_page,
                    linked_url=qr.linked_url,
                    color=qr.color,
                    logo_url=qr.logo_url,
                    qr_code_url=qr.qr_code_url
                )
            if hasattr(page, 'ctas'):
                CTA.objects.create(
                    page=duplicated_page,
                    suggested_cta=page.ctas.suggested_cta,
                    custom_cta=page.ctas.custom_cta,
                    linked_url=page.ctas.linked_url
                )
        return duplicated_magazine

class AIProcess(BaseModel):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In_Progress', 'In Progress'),
        ('Completed', 'Completed'),
        ('Failed', 'Failed'),
    ]

    magazine = models.ForeignKey(Magazine, on_delete=models.CASCADE, related_name='ai_processes')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    progress = models.IntegerField(default=0)
    estimated_time_remaining = models.CharField(max_length=50, default='N/A')

    def __str__(self):
        return f"AIProcess {self.id} for {self.magazine.title}"

class Page(BaseModel):
    magazine = models.ForeignKey(Magazine, on_delete=models.CASCADE, related_name='pages')
    content = models.JSONField()
    accepted = models.BooleanField(default=False)

    def __str__(self):
        return f"Page {self.id} of {self.magazine.title}"

class QRCode(BaseModel):
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='qrcodes')
    linked_url = models.URLField()
    color = models.CharField(max_length=50, default='#000000')
    logo_url = models.URLField(null=True, blank=True)
    qr_code_url = models.URLField()

    def __str__(self):
        return f"QRCode {self.id} for Page {self.page.id}"

class CTA(BaseModel):
    page = models.OneToOneField(Page, on_delete=models.CASCADE, related_name='ctas')
    suggested_cta = models.CharField(max_length=255)
    custom_cta = models.CharField(max_length=255, null=True, blank=True)
    linked_url = models.URLField()

    def __str__(self):
        return f"CTA {self.id} for Page {self.page.id}"

class GeneratedContent(BaseModel):
    page = models.OneToOneField(Page, on_delete=models.CASCADE, related_name='generated_content')
    content = models.JSONField()
    accepted = models.BooleanField(default=False)

    def __str__(self):
        return f"Generated Content {self.id} for Page {self.page.id}"
