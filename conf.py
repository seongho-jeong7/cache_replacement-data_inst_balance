project = "cache_replacement-data_inst_balance"
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
    "ChampSim",
    "ChampSim_DPC4",
    "ChampSim_FDIP",
    "ChampSim_FDIP_dirty",
    "ChampSim_FDIP_ideal",
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
html_static_path = []
