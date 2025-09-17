"""
Setup script for Check Point VM Automation package.
"""

from pathlib import Path

from setuptools import find_packages, setup

# Read the README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    with open(requirements_file, "r", encoding="utf-8") as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="checkpoint-vm-automation",
    version="1.0.0",
    author="Network Automation Team",
    author_email="automation@example.com",
    description="Automation framework for Check Point VM appliances",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/example/checkpoint-vm-automation",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: System :: Networking :: Firewalls",
        "Topic :: System :: Systems Administration",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-mock>=3.8.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=0.991",
        ],
        "docs": [
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.0.0",
        ],
        "nornir": [
            "nornir>=3.3.0",
            "nornir-paramiko>=0.1.0",
        ],
        "ansible": [
            "ansible>=6.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "checkpoint-automation=checkpoint_automation.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "checkpoint_automation": ["config/*.yaml", "config/*.yml"],
    },
)
