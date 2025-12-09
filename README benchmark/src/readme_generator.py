import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional
import pexpect


import os
from huggingface_hub import login

class ReadmeGenerator:
    def __init__(self, tool: str, model: str, repo_path: str, output_path: str, api_key: str, repo_url: str = None):
        self.tool = tool.lower()
        self.model = model
        self.repo_path = repo_path
        self.repo_url = repo_url
        self.output_path = output_path
        self.api_key = api_key

    def run_readmeready(self):
        conda_env_path = "/Users/azat/miniconda3/envs/readmeready"  
        python_exe = Path(conda_env_path) / "bin" / "python" 
        cmd = [
            str(python_exe), 
            str(Path("../ReadMeReady/scripts_local/generate_readme.py").resolve()),
            "--model", self.model,
            "--repo", self.repo_url,
            "--readme-output", self.output_path
        ]
        print(f"Running ReadmeReady: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        print(f"Output written to {self.output_path}")


    def run_larch(self):
        os.environ['EDITOR'] = 'true'  
        conda_env_path = "/Users/azat/miniconda3/envs/larch"  
        python_exe = Path(conda_env_path) / "bin" / "python" 
        
        cmd = f"{python_exe} -m larch.cli --local --model {self.model} --input \"{self.repo_path}\" --out \"{self.output_path}\" --openai-api-key {self.api_key}"

        print(f"Running LARCH automatically: {cmd}")
        child = pexpect.spawn(cmd, encoding='utf-8', timeout=None)
        
        child.logfile_read = sys.stdout
        child.expect("Project name") 
        child.sendline('')
        child.expect("Press enter") 
        child.sendline('')
        child.expect("Finish editing?") 
        child.sendline('N')
        child.expect("Finish editing?") 
        child.sendline('y')

        child.expect(pexpect.EOF)
        print(f"Output written to {self.output_path}")

    async def generate(self):
        if self.tool == "readmeready":
            self.run_readmeready()
        elif self.tool == "larch":
            self.run_larch()
        else:
            raise ValueError(f"Unknown tool: {self.tool}")
