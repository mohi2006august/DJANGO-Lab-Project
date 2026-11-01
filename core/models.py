from django.db import models

class Analysis(models.Model):
    repository_name = models.CharField(max_length=180)
    uploaded_zip = models.FileField(upload_to="repositories/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    file_count = models.PositiveIntegerField(default=0)
    function_count = models.PositiveIntegerField(default=0)
    class_count = models.PositiveIntegerField(default=0)
    total_loc = models.PositiveIntegerField(default=0)
    health_score = models.PositiveIntegerField(default=100)
    health_grade = models.CharField(max_length=10, default="A+")
    is_demo = models.BooleanField(default=False)
    summary = models.TextField(blank=True)
    files_json = models.JSONField(default=list)
    graph_json = models.JSONField(default=dict)
    insights_json = models.JSONField(default=list)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.repository_name} — {self.created_at:%Y-%m-%d %H:%M}"
