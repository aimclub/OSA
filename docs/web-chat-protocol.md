# Web chat protocol

`python -m osa_tool.run_chat --web-chat` runs the agent graph over JSON lines. The normal terminal command remains interactive. Web mode reserves stdout for protocol events and writes diagnostics to stderr and OSA log files. Supply `--output DIR` for a per-run workspace and `--log-dir DIR` for logs.

Send one JSON object per line to stdin. The first message is:

```json
{"type":"start","repository":"https://github.com/owner/repo","request":"Improve the README","attachment":null}
```

OSA sends `started`, `progress`, `review`, `question`, `completed`, `stopped`, or `error` events. A question has an `id`, `question`, `kind`, and `fields` array. Answer it with:

```json
{"type":"answer","id":"QUESTION_ID","values":{"field_name":"value"}}
```

Answer IDs must match the pending question. Required fields need nonempty text; review approval accepts `yes` or `no`. Invalid answers produce a recoverable `error` and leave the question pending. A `{"type":"cancel"}` message stops a run while it is awaiting input; clients should terminate the process group to cancel work in progress.

`completed` contains a summary, task IDs, statuses and results, artifact paths within the requested output directory, and any pull request URL. `stopped` includes a reason. A rejected review at the revision limit stops without finalizing or publishing. A terminal `error` has `recoverable: false` and the process exits nonzero.
