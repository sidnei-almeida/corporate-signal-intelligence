"""Execute a notebook in place, writing outputs back to the .ipynb.

The notebooks are the deliverable for the business case, so their stored outputs
have to match the code that produced them. This runs one headlessly:

    python scripts/run_notebook.py notebooks/data_analysis_cleansing.ipynb

Execution happens with the repository root as the working directory, which is
what the notebooks' relative ``data/`` and ``images/`` paths assume.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import nbformat
from nbclient import NotebookClient

REPO_ROOT = Path(__file__).resolve().parent.parent


def run(path: Path, timeout: int = 3600) -> None:
    nb = nbformat.read(path, as_version=4)
    client = NotebookClient(
        nb,
        timeout=timeout,
        kernel_name="python3",
        resources={"metadata": {"path": str(REPO_ROOT)}},
        allow_errors=False,
    )
    started = time.time()
    client.execute()
    nbformat.write(nb, path)
    print(f"{path.name}: executed {len(nb.cells)} cells in {time.time() - started:.1f}s")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python scripts/run_notebook.py <notebook.ipynb> [...]")
    for arg in sys.argv[1:]:
        run(Path(arg).resolve())
