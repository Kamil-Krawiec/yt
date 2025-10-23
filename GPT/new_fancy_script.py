"""Simple helper script to download ComfyUI models from the Hugging Face Hub."""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

from huggingface_hub import hf_hub_download

ROOT = Path("comfy-data/models")
DIRS = {
    "checkpoints": ROOT / "checkpoints",
    "loras": ROOT / "loras",
    "vae": ROOT / "vae",
    "upscale": ROOT / "upscale_models",
    "controlnet": ROOT / "controlnet",
}
MANIFEST = ROOT / "manifest.json"
NOTES_MD = ROOT / "MODELS_USED.md"

# bundle name -> list of (category, repo, filename, target_dir, rename)
BUNDLES = {
    "sd15-lcm": [
        ("checkpoints", "sd-legacy/stable-diffusion-v1-5", "v1-5-pruned-emaonly.safetensors", DIRS["checkpoints"], None),
        ("loras", "latent-consistency/lcm-lora-sdv1-5", "pytorch_lora_weights.safetensors", DIRS["loras"], "lcm-lora-sdv1-5.safetensors"),
    ],
    "upscalers": [
        ("upscale", "xinntao/Real-ESRGAN", "weights/RealESRGAN_x4plus.pth", DIRS["upscale"], "RealESRGAN_x4plus.pth"),
        ("upscale", "ZynthModels/4x-UltraSharp", "4x-UltraSharp.pth", DIRS["upscale"], None),
    ],
    "controlnet-canny": [
        ("controlnet", "lllyasviel/ControlNet-v1-1", "control_v11p_sd15_canny.pth", DIRS["controlnet"], None),
    ],
    "flux-schnell": [
        ("checkpoints", "Comfy-Org/flux1-schnell", "flux1-schnell.safetensors", DIRS["checkpoints"], None),
    ],
    "sdxl-turbo": [
        ("checkpoints", "stabilityai/sdxl-turbo", "sdxl-turbo.safetensors", DIRS["checkpoints"], None),
    ],
}

OPTIONAL_FILES = {
    "vae": [
        ("vae", "stabilityai/sd-vae-ft-mse-original", "vae-ft-mse-840000-ema-pruned.safetensors", DIRS["vae"], None),
    ],
}

CPU_NOTES = [
    "## CPU-only suggestion",
    "- Base model: `v1-5-pruned-emaonly.safetensors`",
    "- LoRA: `lcm-lora-sdv1-5.safetensors`",
    "- Optional VAE: `vae-ft-mse-840000-ema-pruned.safetensors`",
    "- Optional upscalers: RealESRGAN_x4plus / 4x-UltraSharp",
]


def ensure_dirs():
    for path in DIRS.values():
        path.mkdir(parents=True, exist_ok=True)
    ROOT.mkdir(parents=True, exist_ok=True)


def download_file(repo, filename, target_dir, rename=None):
    print(f"{repo}/{filename}")
    path = hf_hub_download(repo_id=repo, filename=filename)
    destination = target_dir / (rename or Path(filename).name)
    shutil.copy(path, destination)
    return str(destination)


def write_manifest(installed, add_cpu_notes):
    manifest = {"updated": datetime.utcnow().isoformat() + "Z", "installed": installed}
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    lines = ["# MODELS USED", f"- Updated: {manifest['updated']}"]
    for category, paths in installed.items():
        for path in paths:
            lines.append(f"- {category}: `{Path(path).name}` @ `{path}`")
    NOTES_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download model bundles into comfy-data/models and write a manifest."
    )
    parser.add_argument(
        "--bundle",
        nargs="+",
        default=["sd15-lcm"],
        choices=sorted(BUNDLES.keys()),
        help="One or more bundles to fetch.",
    )
    parser.add_argument("--vae", action="store_true", help="Also fetch SD1.5 VAE.")
    return parser.parse_args()


def main():
    args = parse_args()
    ensure_dirs()

    installed = {}

    for bundle_name in args.bundle:
        for item in BUNDLES[bundle_name]:
            category, repo, filename, target_dir, rename = item
            location = download_file(repo, filename, target_dir, rename)
            installed.setdefault(category, []).append(location)

    if args.vae:
        for item in OPTIONAL_FILES["vae"]:
            category, repo, filename, target_dir, rename = item
            location = download_file(repo, filename, target_dir, rename)
            installed.setdefault(category, []).append(location)

    write_manifest(installed, False)
    print("Done.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[ERROR] {exc}")
        sys.exit(1)
