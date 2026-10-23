#!/bin/sh
# Modelle für ComfyUI auf der iDX laden (23.10.2026). Dateien und Varianten wie in den offiziellen
# ComfyUI-Vorlagen (Comfy-Org/workflow_templates): image_qwen_image_2_1_t2i, …_turbo_t2i,
# image_z_image_turbo, image_chroma_text_to_image. Zusammen rund 77 GB.
set -eu
M=${COMFY_MODELS:-/pfad/zu/comfyui/models}
HF=https://huggingface.co
mkdir -p $M/diffusion_models $M/text_encoders $M/vae

hole() {  # hole <Zielordner> <Repo> <Pfad im Repo>
  ziel="$M/$1/$(basename "$3")"
  if [ -s "$ziel" ]; then echo "vorhanden  $ziel"; return; fi
  echo "lade      $ziel"
  curl -fL --retry 5 --retry-delay 10 -C - -o "$ziel.teil" "$HF/$2/resolve/main/$3"
  mv "$ziel.teil" "$ziel"
}

# Qwen-Image 2.1 (Qwen Research License) und Turbo, beide int8 wie in der Vorlage
hole diffusion_models Comfy-Org/Qwen-Image-2.1 diffusion_models/qwen_image_2.1_int8_convrot.safetensors
hole diffusion_models Comfy-Org/Qwen-Image-2.1 diffusion_models/qwen_image_2.1_turbo_int8_convrot.safetensors
hole text_encoders    Comfy-Org/Qwen-Image-2.1 text_encoders/qwen3.5_9b_qwen_image_2.1_pe_t2i.int8_convrot.safetensors
hole text_encoders    Comfy-Org/Qwen-Image-2.1 text_encoders/qwen3vl_8b_int8_convrot.safetensors
hole vae              Comfy-Org/Qwen-Image-2.1 vae/qwen_image_2.1_vae_bf16.safetensors

# Z-Image Turbo (Apache 2.0)
hole diffusion_models Comfy-Org/z_image_turbo split_files/diffusion_models/z_image_turbo_bf16.safetensors
hole text_encoders    Comfy-Org/z_image_turbo split_files/text_encoders/qwen_3_4b.safetensors
hole vae              Comfy-Org/z_image_turbo split_files/vae/ae.safetensors

# Chroma1-HD (Apache 2.0), T5-XXL als Textkodierer, VAE wie Z-Image (ae.safetensors, schon da)
hole diffusion_models Comfy-Org/Chroma1-HD split_files/diffusion_models/Chroma1-HD.safetensors   # bf16: fp8mixed stürzte am 23.10.2026 auf gfx1100 ab (amdgpu page fault)
hole text_encoders    comfyanonymous/flux_text_encoders t5xxl_fp16.safetensors

echo FERTIG
du -sh $M
