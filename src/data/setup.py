from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="safari-shield",
    version="0.1.0",
    author="Safari-Shield Team",
    author_email="team@safari-shield.com",
    description="Adaptive, Explainable, and Real-Time Fraud Detection System for M-Pesa Transactions",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/safari-shield",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Topic :: Office/Business :: Financial",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "pre-commit>=3.0.0",
        ],
        "docs": [
            "mkdocs>=1.5.0",
            "mkdocs-material>=9.0.0",
            "pdoc>=14.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "safari-train=src.models.train:main",
            "safari-predict=src.models.predict:main",
            "safari-api=src.api.app:main",
            "safari-dashboard=dashboard.app:main",
        ],
    },
)