from django.contrib import admin

from .models import Extraction


@admin.register(Extraction)
class ExtractionAdmin(admin.ModelAdmin):
    # list page
    list_display = ['document', 'model_name', 'duration_ms', 'created']
    search_fields = ['document__original_name']

    # results are never edited by hand
    readonly_fields = [
        'document',
        'raw_text',
        'fields',
        'model_name',
        'duration_ms',
        'created',
    ]