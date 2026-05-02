import os

# On Railway: set BRAIN_DIR=/data/brain so brain files live on the persistent volume.
# Locally defaults to data/brain (relative to project root).
BRAIN_DIR = os.getenv("BRAIN_DIR", "data/brain")


def read_brain_file(filename: str) -> str:
    path = os.path.join(BRAIN_DIR, filename)
    try:
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return f"[{filename}: not found]"


def write_brain_file(filename: str, content: str):
    path = os.path.join(BRAIN_DIR, filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


def append_to_brain_file(filename: str, content: str):
    path = os.path.join(BRAIN_DIR, filename)
    with open(path, "a") as f:
        f.write("\n\n" + content)
