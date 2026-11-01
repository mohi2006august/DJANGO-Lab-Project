from django.contrib import admin
from .models import Analysis

@admin.register(Analysis)
class AnalysisAdmin(admin.ModelAdmin):
    list_display = ("repository_name", "created_at", "file_count", "function_count", "class_count")
    readonly_fields = ("created_at", "files_json", "graph_json", "insights_json", "summary")
