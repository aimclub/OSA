from osa_treesitter import OSA_TreeSitter
from docgen import DocGen

mypath = "test_dir/osa"

ts = OSA_TreeSitter(mypath)

res = ts.analyze_directory(mypath)

ts.log_results(res)

dg = DocGen()

output_file = "examples/str.txt"
with open(output_file, "w") as f:
    f.write(dg.format_structure_openai(res))


form_res = dg.format_structure_openai(res)
documentation = dg.generate_documentation_openai(form_res)

doc_file = "examples/documentation.md"
with open(doc_file, "w") as f:
    f.write(documentation)