# How to Use the Model Fetcher

## Requirements
- Python 3.10+
- `huggingface_hub`:
```bash
pip install -U huggingface_hub
```

## Basic Commands
From the project root run I ran this command in video:
```bash
python new_fancy_script.py --bundle sd15-lcm --vae
```
Another model that was tested by me is dreamshaper7, im really impressed by this model, highly recommend!!!
```bash
 python new_fancy_script.py --bundle dreamshaper7 --vae
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



# Examples of outputs

in output directory you can see example outputs of different WebUI workflows.
- From `workflow_owui_lcm_x2.json` is `*__owui_lcm_x2.png` series.
- From `workflow_owui.json` is `*__owui.png` series.
- From `workflow_owui_lcm_512.json` is `*_owui_lcm_512.png` series.
- From `workflow_deamshaper7_*.json` is `*DreamShaper_*.png` series and I think its the best!
