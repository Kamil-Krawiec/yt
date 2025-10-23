# How to Use the Model Fetcher

## Requirements
- Python 3.10+
- `huggingface_hub`:
```bash
pip install -U huggingface_hub
```

## Basic Command
From the project root run:
```bash
python new_fancy_script.py --bundle sd15-lcm --vae 
```

## Bundle Options
`--bundle` accepts one or more of:
- `sd15-lcm`
- `upscalers`
- `controlnet-canny`
- `flux-schnell`
- `sdxl-turbo`

Example with multiple bundles:
```bash
python new_fancy_script.py --bundle sd15-lcm upscalers
```

## Optional Flags
- `--vae` downloads the SD1.5 VAE.

## Outputs
- `comfy-data/models/manifest.json` – JSON manifest storing the download timestamp and file paths.
