from functools import lru_cache

from langchain.chat_models import init_chat_model


@lru_cache
def get_model(model_name: str, **kwargs):
    return init_chat_model(model=model_name, **kwargs)
