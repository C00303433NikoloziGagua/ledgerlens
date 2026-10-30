from django.contrib import admin

from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    # list page
    list_display = ['original_name', 'owner', 'status', 'document_type', 'created']
    list_filter = ['status', 'document_type']
    search_fields = ['original_name', 'owner__username']

    # set by the app only
    readonly_fields = [
        'id',
        'status',
        'sha256',
        'size',
        'file_type',
        'created',
        'updated',
    ]