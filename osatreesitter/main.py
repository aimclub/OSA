from osa_treesitter import OSA_TreeSitter

mypath = 'test_dir/'

ts = OSA_TreeSitter(mypath)

res = ts.analyze_directory(mypath)

ts.show_results(res)
ts.log_results(res)