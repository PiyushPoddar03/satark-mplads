"""
Upload SATARK-MPLADS full-stack package to Hugging Face Spaces.
"""

from huggingface_hub import HfApi

SPACE_ID = "Piyushpoddar03/satark-mplads"
FOLDER_PATH = r"C:\Users\podda\Desktop\code\satark-hf-space"

api = HfApi()

print(f"Deploying to Hugging Face Space: {SPACE_ID}...")

# Delete leftover files from static SDK
for fname in ["index.html", "style.css"]:
    try:
        api.delete_file(path_in_repo=fname, repo_id=SPACE_ID, repo_type="space")
        print(f"✓ Removed old {fname}")
    except Exception:
        pass

# Upload folder
api.upload_folder(
    folder_path=FOLDER_PATH,
    repo_id=SPACE_ID,
    repo_type="space",
    commit_message="Deploy full-stack SATARK-MPLADS Docker container (FastAPI + Next.js + NGINX)",
    ignore_patterns=[
        ".git/*",
        ".git",
        ".dockerignore",
        "*.pyc",
        "__pycache__/*",
        "node_modules/*",
        ".next/*",
        "satark.db",
        "storage/evidence/*",
    ],
)

print(f"\n🎉 Deployment successfully uploaded to https://huggingface.co/spaces/{SPACE_ID}")
