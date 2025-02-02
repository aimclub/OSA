# Open-Source-Advisor
Tool that just makes your open source project better

### How to use readme generator:

You need to pass **URL of the GitHub repository**, **LLM API service provider** and **Specific LLM model to use**

#### Examples below:

Local Llama ITMO:
```sh
python main.py https://github.com/ITMO-NSS-team/nas-fedot llama llama
```  
OpenAI:
```sh
python main.py https://github.com/ITMO-NSS-team/nas-fedot openai gpt-3.5-turbo
```
VseGPT:
```sh
python main.py https://github.com/ITMO-NSS-team/nas-fedot vsegpt openai/gpt-3.5-turbo
```
