project = "Balanced L2 Cache"
author = "cache_replacement-data_inst_balance contributors"
copyright = "2026, cache_replacement-data_inst_balance contributors"

extensions = [
    "myst_parser",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

root_doc = "index"
language = "ko"

exclude_patterns = [
    ".agents",
    ".codex",
    ".git",
    ".venv",
    "*_debug",
    "**/*_debug",
    "ChampSim*",
    "README.md",
    "html",
    "outputs",
    "traces",
]

html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "collapse_navigation": False,
    "navigation_depth": 3,
}
html_static_path = ["_static"]
html_css_files = ["custom.css"]
