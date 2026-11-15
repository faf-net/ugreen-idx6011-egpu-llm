# OpenCode with the local models

**English** · [Deutsch](README.de.md)

[OpenCode](https://opencode.ai) is a coding agent for the terminal. With `opencode.jsonc` from this folder it uses
the models on the NAS through llama-swap instead of a cloud service.

```bash
mkdir -p ~/.config/opencode
cp opencode.jsonc ~/.config/opencode/opencode.jsonc     # then enter llama-swap's address
opencode
```

What I learned:

- **One request at a time.** Strata answers one request after the other. If the agent or the chat is writing,
  OpenCode waits, and the other way round.
- **Same model everywhere.** llama-swap keeps exactly one model on the card. If OpenCode asks for a different
  model than the chat or the agent, they throw each other out and every switch costs about 20 seconds. That is
  also why the title agent uses the same model as the work.
- **Few tools.** Every tool description is read with each request. An MCP server with several hundred tools
  cost my local model minutes per turn; I keep such servers switched off and enable them when needed.
- **The file is in OpenCode 2's own format.** OpenCode 2 still reads the older v1 format and converts it, but in
  my case it dropped the image input of a model on the way.
