"""Package metadata for the paper-trading portfolio project."""
from pathlib import Path
from setuptools import find_packages, setup

ROOT = Path(__file__).parent
requirements = [
    line.strip() for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    if line.strip() and not line.startswith("#")
]

setup(
    name="micro-trading-bot-paper",
    version="0.1.0",
    author="Argyris Vivelis",
    description="Paper-trading research bot with a read-only monitoring dashboard",
    long_description=(ROOT / "README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    python_requires=">=3.11",
    packages=find_packages(),
    py_modules=["config", "runtime_control"],
    install_requires=requirements,
    extras_require={
        "test": ["pytest>=7.4,<9"],
        "postgresql": ["psycopg2-binary>=2.9,<3"],
    },
    package_data={"webapp": ["static/*.html", "static/assets/*.css", "static/assets/*.js"]},
)
