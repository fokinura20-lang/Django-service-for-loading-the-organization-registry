from django.contrib import admin
from .models import Organization, FileLoad, LoadError


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('inn', 'name', 'region', 'employees', 'registration_date')
    list_filter = ('region',)
    search_fields = ('inn', 'name')


@admin.register(FileLoad)
class FileLoadAdmin(admin.ModelAdmin):
    list_display = ('filename', 'status', 'started_at', 'finished_at', 'rows_count', 'loaded_count', 'error_count', 'duplicate_count')
    list_filter = ('status',)


@admin.register(LoadError)
class LoadErrorAdmin(admin.ModelAdmin):
    list_display = ('load', 'row_number', 'error_message', 'created_at')
    list_filter = ('load',)