from django.contrib import admin
from .models import TikTokVideo

@admin.register(TikTokVideo)
class TikTokVideoAdmin(admin.ModelAdmin):
    list_display = ('tiktok_video_url', 'ai_processed', 'created_at', 'updated_at')
    list_filter = ('ai_processed', 'created_at', 'updated_at')
    search_fields = ('tiktok_video_url', 'transcription', 'generated_caption')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('tiktok_video_url', 'downloaded_video_url')
        }),
        ('AI Processing', {
            'fields': ('ai_processed', 'transcription', 'generated_caption')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ('tiktok_video_url',)
        return self.readonly_fields