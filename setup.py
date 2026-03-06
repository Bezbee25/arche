from setuptools import setup, find_packages

setup(
    name="arche",
    version="0.1.0",
    # Packages (core/, agents/, web/)
    packages=find_packages(),
    # Module racine arche.py
    py_modules=["arche"],
    install_requires=[
        "typer>=0.9.0,<1.0.0",
        "rich>=13.7.0,<14.0.0",
        "fastapi>=0.110.0,<1.0.0",
        "uvicorn[standard]>=0.29.0,<1.0.0",
        "websockets>=12.0",
        "ptyprocess>=0.7.0",
        "pyyaml>=6.0.1",
        "python-multipart>=0.0.9",
    ],
    entry_points={
        "console_scripts": [
            "arche=arche:app",
        ],
    },
    python_requires=">=3.11",
)
