import json
import time
from openai import AsyncOpenAI
from pydantic import BaseModel
from .config import config

class LLMResponse(BaseModel):
    text: str
    usage: dict
    duration: float

class DeepSeekClient:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            base_url="https://api.deepseek.com"
        )
    
    async def chat(self, system: str, messages: list[dict], model: str = None, temperature: float = None, max_tokens: int = 4096, response_format=None) -> LLMResponse:
        start_time = time.time()
        model = model or config.executor_model
        temperature = temperature if temperature is not None else config.executor_temperature
        
        kwargs = {
            "model": model,
            "messages": [{"role": "system", "content": system}] + messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format
            
        try:
            response = await self.client.chat.completions.create(**kwargs)
            duration = time.time() - start_time
            
            prompt_tokens = response.usage.prompt_tokens if response.usage else 0
            completion_tokens = response.usage.completion_tokens if response.usage else 0
            total_tokens = response.usage.total_tokens if response.usage else 0
            cost = (prompt_tokens * 0.00014 + completion_tokens * 0.00028) / 1000.0
            
            return LLMResponse(
                text=response.choices[0].message.content,
                usage={
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "estimated_cost": cost
                },
                duration=duration
            )
        except Exception as e:
            raise Exception(f"API Error: {str(e)}")
