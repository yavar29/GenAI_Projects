# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Prepare a Vertex AI RAG corpus for the Weather app.

- Creates (or finds) a weather physics corpus
- Uploads multiple PDFs from URLs, local filesystem, or GCS URIs
- Stores the resolved corpus resource name into ../../.env (RAG_CORPUS)
- Lists files in the corpus at the end

Usage (examples):
    python prepare_corpus_and_data.py
    python prepare_corpus_and_data.py --pdf heat_waves.pdf --pdf precipitation_floods.pdf
    python prepare_corpus_and_data.py --pdf https://example.com/wind_storms.pdf
    python prepare_corpus_and_data.py --pdf gs://my-bucket/weather/*.pdf
"""

from google.auth import default
from google.api_core.exceptions import ResourceExhausted
import vertexai
from vertexai.preview import rag

import argparse
import glob
import os
import re
import sys
import tempfile
from typing import Iterable, List, Tuple
from urllib.parse import urlparse

from dotenv import load_dotenv, set_key
import requests

# --- Load environment (.env two levels up, matching ADK sample layout) ---
load_dotenv()

# --- Required envs ---
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
if not PROJECT_ID:
    raise ValueError("GOOGLE_CLOUD_PROJECT not set in .env")

LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION")
if not LOCATION:
    raise ValueError("GOOGLE_CLOUD_LOCATION not set in .env")

# You can override these by flags if you want, but defaults are good.
CORPUS_DISPLAY_NAME = os.getenv("GOOGLE_RAG_CORPUS_DISPLAY_NAME", "Weather_Physics_Corpus")
CORPUS_DESCRIPTION = os.getenv(
    "GOOGLE_RAG_CORPUS_DESCRIPTION",
    "Corpus with concise PDFs explaining weather physics (heat waves, precipitation, winds)."
)

# Path to the root .env (two levels up from this script, like the ADK example)
ENV_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# Default seed PDFs (you can delete/replace these or pass --pdf flags)
DEFAULT_PDFS: List[str] = [
    # Local filenames (if present in your repo or runtime):
    # "heat_waves.pdf",
    # "precipitation_floods.pdf",
    # "wind_storms.pdf",

    # Or URLs (the script will download and upload):
    # "https://my-site/path/heat_waves.pdf",
    # "https://my-site/path/precipitation_floods.pdf",
    # "https://my-site/path/wind_storms.pdf",
]


def initialize_vertex_ai():
    credentials, _ = default()
    vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)


def create_or_get_corpus():
    """Create a new corpus or return existing one by display name."""
    embedding_model_config = rag.EmbeddingModelConfig(
        publisher_model="publishers/google/models/text-embedding-004"
    )
    corpus = None
    for existing_corpus in rag.list_corpora():
        if getattr(existing_corpus, "display_name", "") == CORPUS_DISPLAY_NAME:
            corpus = existing_corpus
            print(f"Found existing corpus '{CORPUS_DISPLAY_NAME}'")
            break

    if corpus is None:
        corpus = rag.create_corpus(
            display_name=CORPUS_DISPLAY_NAME,
            description=CORPUS_DESCRIPTION,
            embedding_model_config=embedding_model_config,
        )
        print(f"Created new corpus '{CORPUS_DISPLAY_NAME}'")

    return corpus


def is_url(path: str) -> bool:
    try:
        p = urlparse(path)
        return p.scheme in ("http", "https")
    except Exception:
        return False


def is_gcs_uri(path: str) -> bool:
    return path.startswith("gs://")


def filename_from_path(path: str) -> str:
    if is_url(path):
        # Try to keep last path segment; fall back to a sanitized name
        name = os.path.basename(urlparse(path).path) or "download.pdf"
        if not name.lower().endswith(".pdf"):
            name += ".pdf"
        return name
    return os.path.basename(path)


def download_pdf(url: str, dest_dir: str) -> str:
    print(f"Downloading PDF: {url}")
    resp = requests.get(url, stream=True, timeout=60)
    resp.raise_for_status()
    out_path = os.path.join(dest_dir, filename_from_path(url))
    with open(out_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    print(f"Saved to {out_path}")
    return out_path


def resolve_inputs(pdf_args: List[str]) -> List[str]:
    """Expand globs, keep URLs and local paths as-is, and return a concrete list."""
    inputs: List[str] = []
    candidates = (pdf_args or DEFAULT_PDFS)
    for item in candidates:
        if is_url(item) or is_gcs_uri(item):
            inputs.append(item)
        elif any(ch in item for ch in ["*", "?", "["]):  # glob
            matched = glob.glob(item)
            if not matched:
                print(f"Warning: glob did not match any files: {item}")
            inputs.extend(matched)
        else:
            inputs.append(item)
    return inputs


def upload_pdf_to_corpus(corpus_name: str, pdf_path: str, display_name: str, description: str) -> bool:
    """Uploads either a local path or a GCS URI to the corpus via rag.upload_file()."""
    try:
        rag_file = rag.upload_file(
            corpus_name=corpus_name,
            path=pdf_path,               # local path or gs:// URI is supported
            display_name=display_name,
            description=description,
        )
        print(f"Uploaded: {display_name}  →  {rag_file.name}")
        return True
    except ResourceExhausted as e:
        print(f"Quota error while uploading {display_name}: {e}")
        print("See README/Troubleshooting to request an embedding quota increase.")
        return False
    except Exception as e:
        print(f"Error uploading {display_name}: {e}")
        return False


def update_env_file(corpus_name: str, env_file_path: str):
    """Writes/updates RAG_CORPUS in the repo .env so agents can pick it up."""
    try:
        set_key(env_file_path, "RAG_CORPUS", corpus_name)
        print(f"Updated RAG_CORPUS in {env_file_path} → {corpus_name}")
    except Exception as e:
        print(f"Error updating .env: {e}")


def list_corpus_files(corpus_name: str):
    files = list(rag.list_files(corpus_name=corpus_name))
    print(f"Total files in corpus: {len(files)}")
    for f in files:
        print(f"- {getattr(f, 'display_name', 'unknown')}  ::  {f.name}")


def main(argv: List[str] | None = None):
    parser = argparse.ArgumentParser(description="Prepare Vertex AI RAG corpus for Weather Physics.")
    parser.add_argument(
        "--pdf",
        action="append",
        default=[],
        help="PDF source (local path, URL, or gs://). Repeat for multiple. "
             "Globs like ./pdfs/*.pdf are supported for local files.",
    )
    parser.add_argument(
        "--description",
        default=CORPUS_DESCRIPTION,
        help="Corpus description override.",
    )
    args = parser.parse_args(argv)

    initialize_vertex_ai()
    corpus = create_or_get_corpus()

    # Keep the corpus description up-to-date (optional)
    # (Vertex RAG may not support patching description yet; skip or handle here if needed.)

    # Update .env for agent wiring
    update_env_file(corpus.name, ENV_FILE_PATH)

    inputs = resolve_inputs(args.pdf)
    if not inputs:
        print("No PDFs provided (and DEFAULT_PDFS is empty). Nothing to upload.")
        print("Tip: place files in ./pdfs and run: python prepare_corpus_and_data.py --pdf ./pdfs/*.pdf")
        return

    successes = 0
    with tempfile.TemporaryDirectory() as tmpdir:
        for item in inputs:
            if is_url(item):
                local_path = download_pdf(item, tmpdir)
                disp = filename_from_path(item)
                ok = upload_pdf_to_corpus(
                    corpus_name=corpus.name,
                    pdf_path=local_path,
                    display_name=disp,
                    description="Weather physics reference",
                )
                successes += int(ok)
            else:
                # Local path or gs://
                disp = filename_from_path(item)
                ok = upload_pdf_to_corpus(
                    corpus_name=corpus.name,
                    pdf_path=item,
                    display_name=disp,
                    description="Weather physics reference",
                )
                successes += int(ok)

    print(f"\nUploaded {successes} file(s).")
    list_corpus_files(corpus_name=corpus.name)


if __name__ == "__main__":
    main(sys.argv[1:])


