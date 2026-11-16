# Memory use of 2026-11-16 on Strata 0.2.14

Each model loaded on its own with its production run config, one short request, then 180 s idle; the NAS services running, my agent stopped. Then read: `/proc/<pid>/status` of the largest process in the engine container, `/proc/meminfo`, `mem_info_vram_used` and `_total` of the card, and the engine log of the same run config for the expert cache and the MTP draft.

| File | Model | Engine RSS | RAM available | Expert cache | MTP draft | VRAM used |
|---|---|---:|---:|---:|---:|---:|
| `memory-faber.json` | original IQ3_XXS | 47.16 GiB | 4.49 GiB | 17.01 GiB | 0.99 GiB | 23.29 GiB |
| `memory-liber.json` | uncensored version, in daily use | 42.81 GiB | 7.92 GiB | 14.05 GiB | 1.25 GiB | 23.29 GiB |

The two run configs differ, and most of the gap lies there. The uncensored version runs with image input (`--vision`), without `--kv-resident 32768` (no K/V pinned in RAM: RssShmem 0.67 instead of 4.02 GiB) and with a conversation cache of 2 slots / 4,608 MiB instead of 4 / 9,216 MiB. The image part takes room on the card, so its expert cache is smaller.

The October measurement (`../2026-10-23-v0.2.3.1/memory.json`, original on 0.2.3.1) had 44.6 GiB engine RSS and 7.5 GiB available. The page diagram `speicher` shows the original; the uncensored version is in its footnote.
