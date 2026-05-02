import math
import re
import random
import logging
from typing import Optional, List, Any, Dict, Union

from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatResult
from langchain_core.runnables import RunnableConfig
from pydantic import Field
from core.config import settings

logger = logging.getLogger(__name__)

class LLMServiceError(Exception):
    """Raised when the upstream LLM provider cannot serve the request cleanly."""
    def __init__(
        self,
        detail: str,
        *,
        status_code: int = 503,
        retry_after: Optional[int] = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.retry_after = retry_after

def get_gemini_keys() -> List[str]:
    """
    Retrieves all available Gemini keys. 
    If ENABLE_KEY_ROTATION is False, returns only the primary key.
    """
    primary = settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY
    
    if not settings.ENABLE_KEY_ROTATION:
        return [primary] if primary else []

    keys = []
    # 1. Check for GEMINI_API_KEYS (comma separated)
    if settings.GEMINI_API_KEYS:
        keys.extend([k.strip() for k in settings.GEMINI_API_KEYS.split(",") if k.strip()])
    
    # 2. Check for individual keys GEMINI_API_KEY_1, 2, 3... in environment
    import os
    for i in range(1, 11): # Check up to 10 keys
        k = os.environ.get(f"GEMINI_API_KEY_{i}")
        if k and k.strip() not in keys:
            keys.append(k.strip())
    
    # 3. Add primary keys as well if not already in the list
    if primary and primary not in keys:
        keys.insert(0, primary)
    
    return keys

class RotatedGeminiLLM(BaseChatModel):
    """
    A LangChain compatible ChatModel that wraps multiple Gemini keys and handles rotation/fallback.
    """
    # Use Field to tell Pydantic about this attribute
    internal_models: List[ChatOpenAI] = Field(default_factory=list)
    
    def __init__(self, keys: List[str], model_name: str, temperature: float = 0.2, **kwargs):
        # Create the sub-models
        models = [
            ChatOpenAI(
                model=model_name,
                api_key=key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                temperature=temperature,
            ) for key in keys
        ]
        # Pass to super init as a keyword argument
        super().__init__(internal_models=models, **kwargs)

    def _generate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, run_manager: Optional[Any] = None, **kwargs: Any) -> ChatResult:
        last_error = None
        indices = list(range(len(self.internal_models)))
        random.shuffle(indices)
        
        for idx in indices:
            try:
                return self.internal_models[idx]._generate(messages, stop, run_manager, **kwargs)
            except (RateLimitError, APITimeoutError, APIConnectionError, APIStatusError) as e:
                logger.warning(f"Gemini Key {idx} failed: {e}. Trying next key...")
                last_error = e
                continue
        raise last_error

    async def _agenerate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, run_manager: Optional[Any] = None, **kwargs: Any) -> ChatResult:
        last_error = None
        indices = list(range(len(self.internal_models)))
        random.shuffle(indices)
        
        for idx in indices:
            try:
                return await self.internal_models[idx]._agenerate(messages, stop, run_manager, **kwargs)
            except (RateLimitError, APITimeoutError, APIConnectionError, APIStatusError) as e:
                logger.warning(f"Gemini Key {idx} failed: {e}. Trying next key...")
                last_error = e
                continue
        raise last_error

    def with_structured_output(self, schema: Any, **kwargs: Any):
        from langchain_core.runnables import RunnableLambda
        
        def _get_structured_model(idx: int):
            return self.internal_models[idx].with_structured_output(schema, **kwargs)

        def wrapped_structured_invoke(input_data: Any, config: Optional[RunnableConfig] = None):
            last_error = None
            indices = list(range(len(self.internal_models)))
            random.shuffle(indices)
            
            for idx in indices:
                try:
                    return _get_structured_model(idx).invoke(input_data, config)
                except Exception as e:
                    logger.warning(f"Structured output (sync) failed with Gemini Key {idx}: {e}")
                    last_error = e
                    continue
            raise last_error

        async def wrapped_structured_ainvoke(input_data: Any, config: Optional[RunnableConfig] = None):
            last_error = None
            indices = list(range(len(self.internal_models)))
            random.shuffle(indices)
            
            for idx in indices:
                try:
                    return await _get_structured_model(idx).ainvoke(input_data, config)
                except Exception as e:
                    logger.warning(f"Structured output (async) failed with Gemini Key {idx}: {e}")
                    last_error = e
                    continue
            raise last_error

        return RunnableLambda(wrapped_structured_invoke, afunc=wrapped_structured_ainvoke)

    @property
    def _llm_type(self) -> str:
        return "rotated_gemini"

def get_rotated_gemini(temperature: float = 0.2):
    keys = get_gemini_keys()
    if not keys:
        # Provide a dummy key if none found, but this will fail on first call
        return ChatOpenAI(
            model=settings.GEMINI_MODEL,
            api_key="MISSING",
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            temperature=temperature
        )
    return RotatedGeminiLLM(keys, settings.GEMINI_MODEL, temperature)

def get_llm(temperature: float = 0.2):
    """Alias for getting a rotated Gemini instance."""
    return get_rotated_gemini(temperature)

def get_groq_llm(temperature: float = 0.2):
    """Alias for getting a Groq instance."""
    return ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY or "MISSING",
        temperature=temperature,
    )

# Primary shared models
gemini_llm = get_llm(temperature=0.2)
groq_llm = get_groq_llm(temperature=0.2)

async def call_llm(prompt: str):
    """
    Simplified call_llm that uses the rotated model.
    """
    try:
        response = await gemini_llm.ainvoke(prompt)
        return response.content
    except Exception as e:
        logger.error(f"Gemini rotation failed: {e}. Falling back to Groq.")
        try:
            response = await groq_llm.ainvoke(prompt)
            return response.content
        except Exception as groq_e:
            raise LLMServiceError(f"Both Gemini and Groq failed: {groq_e}")
