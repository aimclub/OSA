import requests
import uuid
import logging


class payloadFactory:
    def __init__(
        self,
        job_id: str,
        prompt: str,
        roles: list,
        temperature: float,
        tokens_limit: int,
    ):
        self.job_id = job_id
        self.temperature = temperature
        self.tokens_limit = tokens_limit
        self.prompt = prompt
        self.roles = roles

    def to_payload(self) -> dict:
        return {
            "job_id": self.job_id,
            "meta": {
                "temperature": self.temperature,
                "tokens_limit": self.tokens_limit,
            },
            "content": self.prompt,
        }

    def to_payload_completions(self) -> dict:
        return {
            "job_id": self.job_id,
            "meta": {
                "temperature": self.temperature,
                "tokens_limit": self.tokens_limit,
            },
            "messages": self.roles,
        }


class requestHandler:
    def __init__(self, server_url):
        self.url = server_url
        self.uuid = str(uuid.uuid4())

    def initialize_payload(
        self,
        prompt: str,
        roles: list = [],
        temperature: float = 0.05,
        tokens_limit: int = 8192,
    ):
        self.payload = payloadFactory(
            self.uuid, prompt, roles, temperature, tokens_limit
        ).to_payload_completions()

    def send_request(self) -> requests.Response:
        response = requests.post(url=self.url, json=self.payload)
        logging.info(response)
        return response
