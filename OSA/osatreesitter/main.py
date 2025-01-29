from osa_treesitter import OSA_TreeSitter
from docgen import DocGen

mypath = "./docgen.py"
ts = OSA_TreeSitter(mypath)
res = ts.analyze_directory(mypath)
ts.log_results(res)
dg = DocGen()
dg.process_python_file(res, mypath)