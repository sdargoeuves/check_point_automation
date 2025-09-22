#!/usr/bin/env python3
"""Setup script for checkpoint-automation package."""

from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="checkpoint-automation",
    version="0.1.0",
    author="Check Point Automation Team",
    description="A Python library for automating Check Point firewall configuration and management",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "paramiko>=2.7.0",
    ],
    entry_points={
        "console_scripts": [
            "checkpoint-set-expert=scripts.fw_set_expert:main",
        ],
    },
)
