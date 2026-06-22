# Paper claims pipeline

The reusable operation lives in `osa_tool.operations.analysis.paper_claims` and exposes a single-document pipeline:

```python
from osa_tool.operations.analysis.paper_claims import PaperClaimPipeline

pipeline = PaperClaimPipeline(model_handler)
result = await pipeline.arun(Path("paper.pdf"))
```

PDFs are split into physical ten-page chunks by default. One Marker converter instance processes the chunks in
order, and successful Marker Markdown is cached beneath the system temporary directory. Section parsing and LLM
claim extraction are intentionally rerun.

`marker-pdf` is loaded lazily and is not declared in OSA's dependency graph. Marker 1.10.2 requires `openai<2`,
while OSA's ProtoLLM dependency requires `openai>=2.6`; declaring both makes the project unsolvable. A runtime that
uses this pipeline must therefore provision Marker separately and verify its non-LLM conversion path with the
installed OpenAI package. OSA does not enable Marker's LLM processors.

Evaluation dependencies are isolated from the runtime requirements:

```bash
pip install -r requirements-paper-claims-eval.txt
python -m osa_tool.tools.paper_claims.evaluate --help
python -m osa_tool.tools.paper_claims.aggregate --help
```
