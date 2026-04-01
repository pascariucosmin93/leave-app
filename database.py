name: CI

on:
  push:
    branches:
      - "**"
  pull_request:

jobs:
  test-and-build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install backend dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r backend/requirements.txt
          pip install pytest

      - name: Run tests
        env:
          UNIT_TESTING: "1"
        run: pytest -q

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Validate backend Docker build
        uses: docker/build-push-action@v6
        with:
          context: ./backend
          push: false

      - name: Validate frontend Docker build
        uses: docker/build-push-action@v6
        with:
          context: ./frontend
          push: false
