# Installation

This document explains how to set up the development environment using `uv` (a lightweight virtual environment wrapper).

## Prerequisites

- Python 3.12 or higher
- `pip` installed

## Setup Steps

1. Install the `uv` tool globally (if you don't have it already):
   ```bash
   pip install uv
   ```

2. Initialize a new virtual environment:
   ```bash
   uv venv .venv --python 3.12.1
   ```
   This creates a `.venv/` directory and prepares the environment.

3. Install the project package and its dependencies:
   ```bash
   uv pip install .
   ```
   This installs the local package (src layout) and any dependencies.

4. Activate the virtual environment (optional; `uv` commands also auto-activate):
   ```bash
   source .venv/bin/activate
   ```

5. Run the application:
   ```bash
   uv run python main.py
   ```

Enjoy developing with Code Review Buddy!
