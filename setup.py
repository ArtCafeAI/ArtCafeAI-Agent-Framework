from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="artcafe-agent",
    version="0.1.0",
    author="ArtCafe Team",
    author_email="support@artcafe.ai",
    description="ArtCafe.ai Agent Framework for building intelligent agents",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/artcafe-ai/agent-framework",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "httpx>=0.24.0",
        "websockets>=11.0",
        "pydantic>=2.0.0",
        "PyJWT>=2.6.0",
        "cryptography>=3.4.8",
        "python-dotenv>=0.19.0",
        "asyncio>=3.4.3",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
        ],
        "examples": [
            "beautifulsoup4>=4.11.0",
            "psutil>=5.9.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "artcafe-agent=framework.cli:main",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/artcafe-ai/agent-framework/issues",
        "Source": "https://github.com/artcafe-ai/agent-framework",
        "Documentation": "https://docs.artcafe.ai",
    },
)