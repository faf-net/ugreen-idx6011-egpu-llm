# Chat and web search for the NAS

**English** · [Deutsch](README.de.md)

Open WebUI and SearXNG in one Compose file, both only in the home network. The language models come from
llama-swap (see `konfig/strata-0.2.12/`).

```bash
cp .env.beispiel .env        # set ADRESSE, LLAMA_SWAP_URL and SEARXNG_SECRET
docker compose up -d
```

Then open `http://<address of the NAS>:3000`. The first account you create becomes the administrator; sign-up is
closed after that, further accounts are created by the administrator.

Tested on 15 Nov 2026 on the iDX6011 Pro (UGOS Pro 1.21.1, Docker Compose 5.1.3), next to the running setup:
first account becomes administrator, a second sign-up is refused, the model list shows the llama-swap models, the
web search returns results, a chat answer comes back. Memory: Open WebUI 689 MiB, SearXNG 139 MiB. With the 125B
model loaded, about 5 GiB of the 64 GB stayed available.

Things to know:

- **Open WebUI computes nothing itself here.** Embedding, reranking and speech models are switched off, because
  memory is tight next to the 125B model. Uploaded documents go into the model's context as a whole.
- **Bind the port to the NAS's address**, not to `0.0.0.0`: published Docker ports bypass the firewall of UGOS.
- **llama-swap listens on the NAS's address, not on localhost.** Use that address in `LLAMA_SWAP_URL`.
- **One model for everyone.** Two people on the same model wait for each other for a few seconds; two people on
  two different models make the card reload on every change, about 20 s each time.
- New folders under `/volume1/docker` inherit an ACL on UGOS; if a container cannot write to `./daten`, set owner
  and permissions explicitly.

The agent is not part of this file: install Hermes Agent the way its own documentation describes and take the
settings from [docs/agent.md](../../docs/agent.md).
