import io
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.files.base import ContentFile
from .forms import RepositoryUploadForm
from .models import Analysis
from .analyzer import analyze_zip, impact_report
from .demo_repo import generate_sample_zip_bytes


def home(request):
    if request.method == "POST":
        form = RepositoryUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded = form.cleaned_data["repository_zip"]
            repo_name = form.cleaned_data["repository_name"].strip()
            try:
                result = analyze_zip(uploaded)
            except ValueError as exc:
                form.add_error("repository_zip", str(exc))
            else:
                analysis = Analysis.objects.create(
                    repository_name=repo_name,
                    uploaded_zip=uploaded,
                    file_count=len(result["files"]),
                    function_count=result["function_count"],
                    class_count=result["class_count"],
                    total_loc=result.get("total_loc", 0),
                    health_score=result.get("health_score", 100),
                    health_grade=result.get("health_grade", "A+"),
                    summary=result["summary"],
                    files_json=result["files"],
                    graph_json=result["graph"],
                    insights_json=result["insights"],
                )
                messages.success(request, f"Successfully decoded '{repo_name}' with {len(result['files'])} modules.")
                return redirect("analysis_detail", pk=analysis.pk)
    else:
        form = RepositoryUploadForm()

    recent = Analysis.objects.order_by("-created_at")[:8]
    demo_exists = Analysis.objects.filter(is_demo=True).exists()

    return render(request, "core/home.html", {
        "form": form,
        "recent": recent,
        "demo_exists": demo_exists,
    })


def load_demo(request):
    """
    Creates or redirects to the interactive demo repository.
    Provides instant 1-click preview without needing to upload anything.
    """
    demo_analysis = Analysis.objects.filter(is_demo=True).first()
    if not demo_analysis:
        zip_bytes = generate_sample_zip_bytes()
        result = analyze_zip(zip_bytes)
        demo_analysis = Analysis.objects.create(
            repository_name="ShopNexus Core (Sample E-Commerce)",
            file_count=len(result["files"]),
            function_count=result["function_count"],
            class_count=result["class_count"],
            total_loc=result.get("total_loc", 0),
            health_score=result.get("health_score", 100),
            health_grade=result.get("health_grade", "A+"),
            is_demo=True,
            summary=result["summary"],
            files_json=result["files"],
            graph_json=result["graph"],
            insights_json=result["insights"],
        )
        demo_analysis.uploaded_zip.save("demo_shopnexus.zip", ContentFile(zip_bytes), save=True)

    messages.info(request, "Loaded demo project: ShopNexus Core Architecture")
    return redirect("analysis_detail", pk=demo_analysis.pk)


def download_sample(request):
    """
    Allows user to download the sample Python repo ZIP directly
    to inspect on their own machine or upload manually.
    """
    zip_bytes = generate_sample_zip_bytes()
    response = HttpResponse(zip_bytes, content_type="application/zip")
    response["Content-Disposition"] = 'attachment; filename="CodeDNA_Sample_Shop.zip"'
    return response


def analysis_detail(request, pk):
    analysis = get_object_or_404(Analysis, pk=pk)
    impact = None
    target = request.GET.get("target") or request.POST.get("target", "")
    target = target.strip()

    if target:
        impact = impact_report(analysis.files_json, analysis.graph_json, target)
        if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("format") == "json":
            return JsonResponse({"impact": impact})

    return render(request, "core/detail.html", {
        "analysis": analysis,
        "impact": impact,
        "target": target,
    })


def export_json(request, pk):
    analysis = get_object_or_404(Analysis, pk=pk)
    data = {
        "repository_name": analysis.repository_name,
        "created_at": analysis.created_at.isoformat(),
        "health_score": analysis.health_score,
        "health_grade": analysis.health_grade,
        "metrics": {
            "file_count": analysis.file_count,
            "function_count": analysis.function_count,
            "class_count": analysis.class_count,
            "total_loc": analysis.total_loc,
            "dependency_edges": len(analysis.graph_json.get("edges", [])),
            "cycles_detected": len(analysis.graph_json.get("cycles", [])),
        },
        "summary": analysis.summary,
        "insights": analysis.insights_json,
        "graph": analysis.graph_json,
        "files": analysis.files_json,
    }
    response = JsonResponse(data, json_dumps_params={"indent": 2})
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in analysis.repository_name)
    response["Content-Disposition"] = f'attachment; filename="codedna_{safe_name}_report.json"'
    return response


def analysis_delete(request, pk):
    if request.method == "POST":
        analysis = get_object_or_404(Analysis, pk=pk)
        repo_name = analysis.repository_name
        analysis.delete()
        messages.success(request, f"Deleted analysis for '{repo_name}'.")
    return redirect("home")
