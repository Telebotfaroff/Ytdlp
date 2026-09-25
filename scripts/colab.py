"""Colab launcher placeholder.

Step 1 only prepares the project. Bot startup will be added in a later step.
"""

from app.config.settings import settings


if __name__ == "__main__":
    settings.prepare_directories()
    print("Project environment initialized for Colab.")
