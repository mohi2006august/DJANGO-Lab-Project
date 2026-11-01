from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("demo/", views.load_demo, name="load_demo"),
    path("sample-download/", views.download_sample, name="download_sample"),
    path("analysis/<int:pk>/", views.analysis_detail, name="analysis_detail"),
    path("analysis/<int:pk>/json/", views.export_json, name="analysis_json"),
    path("analysis/<int:pk>/delete/", views.analysis_delete, name="analysis_delete"),
]

