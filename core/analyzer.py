"""
Static-only Python repository analyzer for CodeDNA.
Extracts AST symbols, resolves internal dependency graphs, calculates coupling metrics,
detects circular dependency cycles, and estimates change blast radii.
Uploaded code is NEVER executed.
"""
import ast
import io
import math
import zipfile
from pathlib import PurePosixPath

MAX_FILES = 600
MAX_PY_FILE_BYTES = 750_000


def analyze_zip(uploaded_file):
    """
    Parses a ZIP archive of Python source files into an architectural AST map.
    Returns:
        dict containing files, graph, insights, summary, counts, health_score, health_grade.
    """
    try:
        if hasattr(uploaded_file, "read"):
            uploaded_file.seek(0)
            zf = zipfile.ZipFile(uploaded_file)
        elif isinstance(uploaded_file, (bytes, bytearray)):
            zf = zipfile.ZipFile(io.BytesIO(uploaded_file))
        else:
            zf = zipfile.ZipFile(uploaded_file)
    except (zipfile.BadZipFile, OSError):
        raise ValueError("The provided file is not a valid or readable ZIP archive.")

    py_files = []
    for info in zf.infolist():
        path = PurePosixPath(info.filename)
        # Skip directories, dotfiles, virtualenvs, cache dirs
        if info.is_dir() or path.is_absolute() or ".." in path.parts:
            continue
        # Skip git, caches, test caches, venvs, node_modules
        skip_dirs = {".git", "__pycache__", ".venv", "venv", "env", ".env", "node_modules", ".tox", ".pytest_cache", ".idea", ".vscode"}
        if any(part in skip_dirs for part in path.parts):
            continue
        if path.suffix == ".py" and info.file_size <= MAX_PY_FILE_BYTES:
            py_files.append(info)
        if len(py_files) >= MAX_FILES:
            break

    records = []
    names = {}
    total_functions = 0
    total_classes = 0
    total_loc = 0

    for info in py_files:
        raw = zf.read(info)
        try:
            source = raw.decode("utf-8")
        except UnicodeDecodeError:
            source = raw.decode("utf-8", errors="replace")

        # Normalize relative path, stripping common root archive folder if any
        path = str(PurePosixPath(info.filename))
        parts = PurePosixPath(path).parts
        if len(parts) > 1 and parts[0].endswith(("-main", "-master")):
            path = str(PurePosixPath(*parts[1:]))

        # Compute dot-separated module identifier
        module = path[:-3].replace("/", ".").replace("\\", ".")
        if module.endswith(".__init__"):
            module = module[:-9]
        if not module:
            module = "root"

        lines = source.splitlines()
        loc_count = len(lines)
        total_loc += loc_count

        try:
            tree = ast.parse(source)
            parse_error = ""
        except SyntaxError as exc:
            tree = None
            parse_error = f"Syntax error at line {exc.lineno}: {exc.msg}"

        functions = []
        classes = []
        raw_imports = []
        complexity = 0
        docstring = ""

        if tree:
            docstring = ast.get_docstring(tree) or ""
            if len(docstring) > 220:
                docstring = docstring[:217] + "..."

            for node in ast.walk(tree):
                # Functions
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    is_async = isinstance(node, ast.AsyncFunctionDef)
                    args = [a.arg for a in node.args.args]
                    decorators = []
                    for d in node.decorator_list:
                        if isinstance(d, ast.Name):
                            decorators.append(d.id)
                        elif isinstance(d, ast.Attribute):
                            decorators.append(f"{getattr(d.value, 'id', '')}.{d.attr}")
                    fn_doc = ast.get_docstring(node) or ""
                    if len(fn_doc) > 140:
                        fn_doc = fn_doc[:137] + "..."
                    functions.append({
                        "name": node.name,
                        "line": node.lineno,
                        "args": args,
                        "is_async": is_async,
                        "decorators": decorators[:3],
                        "docstring": fn_doc,
                    })

                # Classes
                elif isinstance(node, ast.ClassDef):
                    bases = []
                    for b in node.bases:
                        if isinstance(b, ast.Name):
                            bases.append(b.id)
                        elif isinstance(b, ast.Attribute):
                            bases.append(f"{getattr(b.value, 'id', '')}.{b.attr}")
                    cls_doc = ast.get_docstring(node) or ""
                    if len(cls_doc) > 140:
                        cls_doc = cls_doc[:137] + "..."
                    # Find immediate methods
                    methods = []
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            methods.append(item.name)
                    classes.append({
                        "name": node.name,
                        "line": node.lineno,
                        "bases": bases,
                        "methods": methods[:8],
                        "docstring": cls_doc,
                    })

                # Imports
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        raw_imports.append({"name": alias.name, "level": 0})
                elif isinstance(node, ast.ImportFrom):
                    mod_name = node.module or ""
                    level = node.level or 0
                    raw_imports.append({"name": mod_name, "level": level})

                # Cyclomatic Complexity decision points
                elif isinstance(node, (
                    ast.If, ast.For, ast.AsyncFor, ast.While,
                    ast.Try, ast.ExceptHandler, ast.With, ast.AsyncWith,
                    ast.comprehension, ast.BoolOp, ast.Assert
                )):
                    complexity += 1

        total_functions += len(functions)
        total_classes += len(classes)

        # Distinguish internal module candidates from raw imports
        all_import_names = set()
        for item in raw_imports:
            lvl = item["level"]
            name = item["name"]
            if lvl > 0:
                # Relative import resolution
                parent_parts = module.split(".")[:-lvl] if lvl <= len(module.split(".")) else []
                resolved_rel = ".".join(parent_parts + ([name] if name else []))
                if resolved_rel:
                    all_import_names.add(resolved_rel)
            elif name:
                all_import_names.add(name)

        record = {
            "path": path,
            "module": module,
            "filename": PurePosixPath(path).name,
            "lines": loc_count,
            "functions": functions,
            "classes": classes,
            "imports": sorted(all_import_names),
            "complexity": complexity,
            "docstring": docstring,
            "parse_error": parse_error,
        }
        records.append(record)
        names[module] = record

    # Build Graph Nodes & Edges
    edges = []
    in_degrees = {m: 0 for m in names}
    out_degrees = {m: 0 for m in names}

    for record in records:
        source_mod = record["module"]
        for imp in record["imports"]:
            clean_imp = imp.lstrip(".")
            target_mod = None
            if clean_imp in names:
                target_mod = clean_imp
            else:
                # Prefix matching for submodule or symbol imports
                candidates = [n for n in names if clean_imp.startswith(n + ".") or n.startswith(clean_imp + ".")]
                if candidates:
                    target_mod = sorted(candidates, key=len)[0]

            if target_mod and target_mod != source_mod:
                edge = {"from": source_mod, "to": target_mod}
                if edge not in edges:
                    edges.append(edge)
                    out_degrees[source_mod] = out_degrees.get(source_mod, 0) + 1
                    in_degrees[target_mod] = in_degrees.get(target_mod, 0) + 1

    # Detect Circular Dependencies (Cycles) using DFS
    adj = {m: [] for m in names}
    for e in edges:
        adj[e["from"]].append(e["to"])

    detected_cycles = []
    visited = {}
    path_stack = []

    def dfs_find_cycles(node):
        visited[node] = 1  # In progress
        path_stack.append(node)
        for neighbor in adj.get(node, []):
            if visited.get(neighbor) == 1:
                # Found cycle
                cycle_start_idx = path_stack.index(neighbor)
                cycle_path = path_stack[cycle_start_idx:] + [neighbor]
                cycle_str = " → ".join(cycle_path)
                # Avoid duplicate cycle permutations
                normalized_cycle = tuple(sorted(set(cycle_path)))
                if not any(set(cycle_path) == set(c.split(" → ")) for c in detected_cycles):
                    detected_cycles.append(cycle_str)
            elif visited.get(neighbor, 0) == 0:
                dfs_find_cycles(neighbor)
        path_stack.pop()
        visited[node] = 2  # Completed

    for m in names:
        if visited.get(m, 0) == 0:
            dfs_find_cycles(m)

    # Compute Nodes with coupling & instability metrics
    nodes = []
    for r in records:
        m = r["module"]
        ca = in_degrees.get(m, 0)   # Afferent coupling (who depends on this)
        ce = out_degrees.get(m, 0)  # Efferent coupling (who this depends on)
        instability = round(ce / (ca + ce), 2) if (ca + ce) > 0 else 0.5
        role = "service"
        if "model" in m or "schema" in m:
            role = "model"
        elif "view" in m or "api" in m or "route" in m or "controller" in m:
            role = "controller"
        elif "util" in m or "helper" in m or "common" in m:
            role = "utility"
        elif ca >= 2:
            role = "hub"

        nodes.append({
            "id": m,
            "label": PurePosixPath(r["path"]).name,
            "path": r["path"],
            "lines": r["lines"],
            "functions_count": len(r["functions"]),
            "classes_count": len(r["classes"]),
            "complexity": r["complexity"],
            "in_degree": ca,
            "out_degree": ce,
            "instability": instability,
            "role": role,
            "has_error": bool(r["parse_error"]),
        })

    # Calculate Code Health Score (0-100) & Grade
    health_score = 100
    # Penalty for parse errors
    syntax_errors = [r for r in records if r["parse_error"]]
    health_score -= min(35, len(syntax_errors) * 20)

    # Penalty for circular dependencies
    health_score -= min(30, len(detected_cycles) * 15)

    # Penalty for hotspot concentration (single module taking > 60% of all incoming edges)
    if edges:
        max_in = max(in_degrees.values()) if in_degrees else 0
        if max_in >= 4 and max_in / len(edges) > 0.6:
            health_score -= 10

    # Penalty for high average complexity
    avg_complexity = (sum(r["complexity"] for r in records) / len(records)) if records else 0
    if avg_complexity > 8:
        health_score -= 15
    elif avg_complexity > 5:
        health_score -= 8

    health_score = max(20, min(100, health_score))

    if health_score >= 90:
        health_grade = "A+"
    elif health_score >= 80:
        health_grade = "A"
    elif health_score >= 70:
        health_grade = "B"
    elif health_score >= 60:
        health_grade = "C"
    else:
        health_grade = "D"

    # Generate Actionable Insights
    insights = []
    if not records:
        insights.append({
            "type": "error",
            "title": "No Python files found",
            "detail": "This analyzer inspects Python (.py) files. Upload an archive containing source files."
        })
    else:
        insights.append({
            "type": "success",
            "title": "Architecture Mapped",
            "detail": f"Decoded {len(records)} modules across {total_loc:,} lines of code. Discovered {total_functions} functions and {total_classes} classes."
        })

        if detected_cycles:
            insights.append({
                "type": "critical",
                "title": f"Circular Dependency Alert ({len(detected_cycles)} detected)",
                "detail": f"Cycles can cause tight coupling and import order bugs: {', '.join(detected_cycles[:2])}."
            })

        if edges:
            most_imported = max(in_degrees, key=in_degrees.get)
            if in_degrees[most_imported] > 1:
                insights.append({
                    "type": "hotspot",
                    "title": f"Architectural Hotspot: {most_imported}",
                    "detail": f"Imported by {in_degrees[most_imported]} modules. Modifications here have high downstream blast radius."
                })
        else:
            insights.append({
                "type": "info",
                "title": "Decoupled / Isolated Modules",
                "detail": "No internal cross-module imports were resolved. This project may use external frameworks or independent scripts."
            })

        complex_files = sorted(records, key=lambda r: r["complexity"], reverse=True)
        if complex_files and complex_files[0]["complexity"] >= 5:
            insights.append({
                "type": "warning",
                "title": f"High Complexity: {complex_files[0]['filename']}",
                "detail": f"Contains {complex_files[0]['complexity']} branching or control-flow pathways. Recommend adding unit tests before refactoring."
            })

        if syntax_errors:
            insights.append({
                "type": "error",
                "title": f"Syntax Errors in {len(syntax_errors)} File(s)",
                "detail": "These files could not be parsed by Python's AST compiler. Inspect file details for exact line numbers."
            })

    summary = (
        f"CodeDNA decoded {len(records)} Python source files ({total_loc:,} lines). "
        f"Identified {total_functions} functions, {total_classes} classes, and {len(edges)} internal dependency links. "
        f"Overall architectural health score: {health_score}/100 ({health_grade})."
    )

    return {
        "files": records,
        "graph": {
            "nodes": nodes,
            "edges": edges,
            "cycles": detected_cycles,
        },
        "insights": insights,
        "summary": summary,
        "function_count": total_functions,
        "class_count": total_classes,
        "total_loc": total_loc,
        "health_score": health_score,
        "health_grade": health_grade,
    }


def impact_report(files, graph, target):
    """
    Simulates downstream change blast radius for a given module or filename.
    Returns:
        dict with found status, affected dependents (direct and transitive), risk tier, and advice.
    """
    by_module = {item["module"]: item for item in files}
    cleaned_target = target.strip()
    if cleaned_target.endswith(".py"):
        cleaned_target = cleaned_target[:-3]

    # Find matching module
    matched = None
    for m in by_module:
        if m == cleaned_target:
            matched = m
            break
        if m.endswith("." + cleaned_target) or m.split(".")[-1] == cleaned_target:
            matched = m
            break
        if PurePosixPath(by_module[m]["path"]).name == target.strip():
            matched = m
            break

    if not matched:
        return {
            "found": False,
            "target": target,
            "message": f"No module matching '{target}' was found in this repository.",
            "suggestion": "Select a module name or file from the inventory list below."
        }

    # Reverse adjacency: edge target -> set of modules that import it
    reverse_graph = {}
    forward_graph = {}
    for edge in graph.get("edges", []):
        reverse_graph.setdefault(edge["to"], set()).add(edge["from"])
        forward_graph.setdefault(edge["from"], set()).add(edge["to"])

    direct_dependents = sorted(reverse_graph.get(matched, set()))

    # Traverse all transitive dependents using BFS
    visited_dependents = set()
    queue = list(direct_dependents)
    for d in direct_dependents:
        visited_dependents.add(d)

    transitive_dependents = set()
    while queue:
        curr = queue.pop(0)
        for dep in reverse_graph.get(curr, set()):
            if dep != matched and dep not in visited_dependents:
                visited_dependents.add(dep)
                transitive_dependents.add(dep)
                queue.append(dep)

    total_affected = sorted(visited_dependents)
    upstream_dependencies = sorted(forward_graph.get(matched, set()))
    total_repo_files = len(files)
    blast_radius_pct = round((len(total_affected) / max(1, total_repo_files)) * 100, 1)

    # Risk level assessment
    if len(total_affected) >= 5 or blast_radius_pct >= 40:
        risk_level = "Critical"
        risk_class = "risk-critical"
        risk_color = "#ef4444"
    elif len(total_affected) >= 3 or blast_radius_pct >= 25:
        risk_level = "High"
        risk_class = "risk-high"
        risk_color = "#f97316"
    elif len(total_affected) >= 1:
        risk_level = "Moderate"
        risk_class = "risk-moderate"
        risk_color = "#eab308"
    else:
        risk_level = "Low"
        risk_class = "risk-low"
        risk_color = "#22c55e"

    return {
        "found": True,
        "module": matched,
        "path": by_module[matched]["path"],
        "lines": by_module[matched]["lines"],
        "functions_count": len(by_module[matched]["functions"]),
        "classes_count": len(by_module[matched]["classes"]),
        "direct_dependents": direct_dependents,
        "transitive_dependents": sorted(transitive_dependents),
        "total_affected": total_affected,
        "upstream_dependencies": upstream_dependencies,
        "blast_radius_pct": blast_radius_pct,
        "risk_level": risk_level,
        "risk_class": risk_class,
        "risk_color": risk_color,
        "message": (
            f"Modifying '{matched}' impacts {len(total_affected)} downstream module(s) ({blast_radius_pct}% of the codebase)."
            if total_affected else
            f"'{matched}' has no resolved downstream dependents. Modifying it is low risk."
        ),
        "guidance": [
            f"Review signatures of public functions/classes in {matched}.",
            f"Run tests for the {len(direct_dependents)} direct dependent module(s) first.",
            "Verify backward-compatibility before altering return schemas or exception types."
        ] if total_affected else [
            f"'{matched}' is a leaf or decoupled node; changes will not ripple into other project modules.",
            "Ensure local unit tests pass."
        ]
    }
