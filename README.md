# CodeDNA — Django Codebase Intelligence Platform

> **Static AST Code Decomposition, Force-Directed Dependency Visualization, and Downstream Blast Radius Simulation for Python Architectures.**

CodeDNA is an architectural intelligence platform built in Django. It parses uploaded Python repositories as Abstract Syntax Trees (AST) without executing untrusted code, reconstructs cross-module import topologies, detects circular dependencies, calculates architectural health scores, and estimates change blast radii before refactoring.

---

## ✨ Features

- **⚡ Zero Code Execution**: Analyzes Python repositories strictly via static AST compilation. Uploaded code is never run in Python runtime.
- **🕸️ Interactive Force-Directed Architecture Map**:
  - Physics-based dynamic canvas simulation with Retina / high-DPI scaling.
  - Interactive drag-and-drop of modules to reorganize topologies.
  - Smooth pan and zoom controls, view reset, and fullscreen presentation.
  - Color-coded node classification: Hotspot hubs, Models, Controllers/APIs, and Utilities.
  - Live Inspector Drawer displaying LOC, functions, classes, afferent ($C_a$), efferent ($C_e$), and instability metrics.
- **💥 Downstream Blast Radius Simulator**:
  - Traces direct (1 hop) and transitive (cascading) downstream dependencies.
  - Categorizes risk tiers: Low, Moderate, High, and Critical.
  - Visual blast-radius meter with automated refactoring guidance.
  - Highlighting synchronized directly with the architecture graph.
- **🔄 Circular Dependency Radar**:
  - Automated depth-first cycle traversal to locate circular imports (e.g., `A → B → C → A`).
- **🛡️ Architecture Health Score & Grade**:
  - Synthesizes coupling concentration, cycle presence, complexity distribution, and parsing errors into an overall health rating ($A+$, $A$, $B$, $C$, $D$).
- **🎨 Modern Dark UI System**:
  - Sleek glassmorphism panels, multi-stop gradient accents, and typography powered by *Plus Jakarta Sans* and *JetBrains Mono*.
- **⚡ 1-Click Instant Demo**:
  - Built-in multi-tier e-commerce store (`ShopNexus Core`) available for instant exploration without uploading files.
- **🔍 Real-Time Symbol Inventory**:
  - Search and filter files, classes, and functions as you type.
- **📥 Export Capabilities**:
  - Structured JSON export for CI/CD reporting and 1-click Markdown summary copying.

---

## 🚀 Quickstart

### Prerequisites
- Python 3.10+
- `pip`

### 1. Clone & Set Up Environment

```bash
git clone https://github.com/mohi2006august/DJANGO-Lab-Project.git
cd DJANGO-Lab-Project

# Create virtual environment
python -m venv .venv

# Activate environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 2. Run Database Migrations

```bash
python manage.py migrate
```

### 3. Start Development Server

```bash
python manage.py runserver
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser.

---

## 📂 Project Structure

```text
DJANGO-Lab-Project/
├── codedna/                   # Django project configuration
│   ├── settings.py            # Core settings, database, and apps
│   ├── urls.py                # Root URL router
│   ├── wsgi.py                # WSGI application entry
│   └── __init__.py
├── core/                      # Main application
│   ├── admin.py               # Django admin registrations
│   ├── analyzer.py            # Static AST parser and impact simulator
│   ├── apps.py                # App configuration
│   ├── demo_repo.py           # In-memory sample repository generator
│   ├── forms.py               # Repository upload form & validation
│   ├── models.py              # Analysis database model
│   ├── urls.py                # Core application routes
│   └── views.py               # Request handlers and API endpoints
├── static/                    # Frontend assets
│   └── core/
│       ├── graph.js           # Physics canvas dependency visualizer
│       └── style.css          # Design system & dark mode styles
├── templates/                 # HTML templates
│   └── core/
│       ├── base.html          # Global layout & navigation
│       ├── home.html          # Upload portal & recent analyses
│       └── detail.html        # Interactive report & visualizer
├── sample_repository/         # Bundled sample repository
├── manage.py                  # Django management CLI
├── requirements.txt           # Python package dependencies
└── README.md                  # Documentation
```

---

## 🔒 Security & Privacy

- **Static analysis only**: Files in uploaded ZIPs are extracted in memory and parsed into syntax trees using Python's `ast` module. Code is **never imported, executed, or eval'd**.
- Archive validation enforces a strict 15 MB file size limit and skips suspicious paths (`..`, absolute paths, symlinks, hidden dotfiles).

---

## 📜 License

MIT License. Designed for codebase intelligence, architectural visualization, and software engineering coursework.
