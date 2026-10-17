# Strata (HIP/ROCm) für die RX 7900 XTX (gfx1100) — reproduzierbarer Bauweg.
# Angelegt 17.10.2026. Vorher wurde die Engine von Hand in einem Ubuntu-Container gebaut
# (Image per docker commit, Code/venv/Engine per Bind-Mount). Diese Datei hält denselben Weg reproduzierbar fest.
#
# Bauen auf dem Rechner, auf dem es läuft (die Engine wird für dessen CPU optimiert):
#   docker build -t strata-hip:v0.1.45 --build-arg STRATA_REF=v0.1.45 .
# Stand: siehe README.md (Bauprotokoll).

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 LANG=C.UTF-8
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential ca-certificates curl git python3 python3-pip python3-venv unzip libatomic1 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

ARG STRATA_REF=v0.1.45
# ROCm aus AMDs TheRock-Wheels, Version wie Strata sie für gfx110X festlegt (setup.py: ROCM_VERSION_DEFAULT)
ARG ROCM_INDEX=https://rocm.nightlies.amd.com/v2/gfx110X-dgpu/
ARG ROCM_WHEEL=7.10.0a20251120
ARG GPU_ARCH=gfx1100

WORKDIR /strata
RUN git clone --filter=blob:none https://github.com/Niko1221/Strata src && git -C src checkout -q "$STRATA_REF"
WORKDIR /strata/src

RUN python3 -m venv .venv \
    && .venv/bin/pip install --no-cache-dir --upgrade pip \
    && .venv/bin/pip install --no-cache-dir -r requirements.txt cmake ninja \
    && .venv/bin/pip install --no-cache-dir --index-url "$ROCM_INDEX" "rocm[libraries,devel]==$ROCM_WHEEL"

# llama.cpp am Commit, den setup.py festlegt (LLAMA_CPP_COMMIT), als Zip wie setup.py es holt
RUN .venv/bin/python -c "import setup; setup.get_llama_cpp()"

# "rocm-sdk path --root" packt beim ersten Aufruf die Entwicklerdateien aus (u. a. hip-lang für CMake).
# Ohne diesen Aufruf scheitert enable_language(HIP), gemessen beim ersten Bau am 17.10.2026.
RUN set -e; SP=/strata/src/.venv/lib/python3.12/site-packages; R=$(/strata/src/.venv/bin/rocm-sdk path --root); L=$SP/_rocm_sdk_libraries_gfx110X_dgpu; \
    echo "ROCm-Wurzel: $R"; \
    BC=$(ls -d $R/lib/llvm/amdgcn/bitcode $R/amdgcn/bitcode 2>/dev/null | head -1); \
    export HIP_PLATFORM=amd HIP_COMPILER=clang HIP_RUNTIME=rocclr ROCM_PATH=$R HIP_PATH=$R \
           PATH=$R/bin:$R/llvm/bin:/strata/src/.venv/bin:$PATH LD_LIBRARY_PATH=$R/lib:$L/lib; \
    cmake -G Ninja -S . -B build-hip -DCMAKE_BUILD_TYPE=Release \
      -DSTRATA_ENABLE_HIP=ON -DSTRATA_ENABLE_CUDA=OFF -DSTRATA_BUILD_TESTS=OFF -DSTRATA_PREFILL_MMQ=ON \
      -DCMAKE_HIP_ARCHITECTURES=$GPU_ARCH -DCMAKE_HIP_COMPILER=$R/llvm/bin/clang++ -DCMAKE_HIP_COMPILER_ROCM_ROOT=$R \
      "-DCMAKE_PREFIX_PATH=$R;$L" "-DCMAKE_HIP_FLAGS=--rocm-path=$R --rocm-device-lib-path=$BC" \
      -DSTRATA_GGML_DIR=/strata/src/third_party/llama.cpp; \
    cmake --build build-hip --target strata -j "$(( $(nproc) / 2 ))"; \
    mkdir -p engine; install -m 755 build-hip/strata engine/strata; \
    engine/strata --version

# Modelle, Packs, MTP-Kopf und Konfigurationen kommen per Bind-Mount nach /strata/data bzw. als --config-Datei.
# Start wie in llama-swap: .venv/bin/python serve/server.py --engine strata --port <p> --config <datei.json>
CMD ["/strata/src/.venv/bin/python", "serve/server.py", "--help"]
