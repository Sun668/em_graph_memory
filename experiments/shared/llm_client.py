from __future__ import annotations

import openai
from openai import OpenAI
import numpy as np
import json
import time
import sys
import os
from typing import Optional

_openai_client: Optional[OpenAI] = None


def get_default_openai_model() -> str:
    return os.environ.get("OPENAI_MODEL", "deepseek-v4-pro")


def _get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        set_openai_key()
    return _openai_client


def get_openai_embedding(texts, model="text-embedding-ada-002"):
    client = _get_openai_client()
    texts = [text.replace("\n", " ") for text in texts]
    response = client.embeddings.create(input=texts, model=model)
    return np.array([response.data[i].embedding for i in range(len(texts))])


def set_anthropic_key():
    pass


def set_gemini_key():
    import google.generativeai as genai

    genai.configure(api_key=os.environ['GOOGLE_API_KEY'])


def set_openai_key():
    global _openai_client
    _openai_client = OpenAI(
        api_key=os.environ.get('OPENAI_API_KEY'),
        base_url=os.environ.get('OPENAI_BASE_URL', 'https://openrouter.ai/api/v1'),
    )


def run_json_trials(query, num_gen=1, num_tokens_request=1000,
                model=None, use_16k=False, temperature=1.0, wait_time=1, examples=None, input=None):

    run_loop = True
    counter = 0
    while run_loop:
        try:
            if examples is not None and input is not None:
                output = run_chatgpt_with_examples(query, examples, input, num_gen=num_gen, wait_time=wait_time,
                                                   num_tokens_request=num_tokens_request, use_16k=use_16k, temperature=temperature,
                                                   model=model).strip()
            else:
                output = run_chatgpt(query, num_gen=num_gen, wait_time=wait_time, model=model,
                                                   num_tokens_request=num_tokens_request, use_16k=use_16k, temperature=temperature)
            output = output.replace('json', '')
            facts = json.loads(output.strip())
            run_loop = False
        except json.decoder.JSONDecodeError:
            counter += 1
            time.sleep(1)
            print("Retrying to avoid JsonDecodeError, trial %s ..." % counter)
            print(output)
            if counter == 10:
                print("Exiting after 10 trials")
                sys.exit()
            continue
    return facts


def run_claude(query, max_new_tokens, model_name):
    from anthropic import Anthropic

    if model_name == 'claude-sonnet':
        model_name = "claude-3-sonnet-20240229"
    elif model_name == 'claude-haiku':
        model_name = "claude-3-haiku-20240307"

    client = Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
    )
    message = client.messages.create(
        max_tokens=max_new_tokens,
        messages=[
            {
                "role": "user",
                "content": query,
            }
        ],
        model=model_name,
    )
    print(message.content)
    return message.content[0].text


def run_gemini(model, content: str, max_tokens: int = 0):

    try:
        response = model.generate_content(content)
        return response.text
    except Exception as e:
        print(f'{type(e).__name__}: {e}')
        return None


def run_chatgpt(query, num_gen=1, num_tokens_request=1000,
                model=None, use_16k=False, temperature=1.0, wait_time=1,
                max_retries=10, max_wait=30, timeout=60):

    MODEL_ALIASES = {
        'chatgpt': 'gpt-3.5-turbo',
    }
    actual_model = get_default_openai_model() if model is None else MODEL_ALIASES.get(model, model)

    # Subscription-path models (ChatGPT login via Codex CLI), not Platform API key.
    try:
        from experiments.shared.codex_llm_client import is_codex_model, run_codex_completion
    except Exception:
        is_codex_model = None  # type: ignore
        run_codex_completion = None  # type: ignore
    if is_codex_model is not None and is_codex_model(actual_model):
        return run_codex_completion(
            query,
            model=actual_model,
            timeout=max(int(timeout or 60), 120),
            max_retries=max(1, int(max_retries or 1)),
            wait_time=float(wait_time or 1),
        )

    client = _get_openai_client()
    completion = None
    retries = 0
    model_l = str(actual_model or "").lower()
    uses_completion_tokens = (
        model_l.startswith("gpt-5")
        or model_l.startswith("o1")
        or model_l.startswith("o3")
    )

    while completion is None and retries < max_retries:
        current_wait = min(wait_time * (2 ** retries), max_wait)
        try:
            messages = [{"role": "user", "content": query}]
            kwargs = {
                "model": actual_model,
                "n": num_gen,
                "messages": messages,
                "timeout": timeout,
            }
            if uses_completion_tokens:
                # gpt-5 / o-series reject max_tokens and non-default temperature.
                kwargs["max_completion_tokens"] = num_tokens_request
            else:
                kwargs["max_tokens"] = num_tokens_request
                kwargs["temperature"] = temperature
            completion = client.chat.completions.create(**kwargs)
        except openai.APIError as e:
            retries += 1
            print(f"OpenAI API Error (retry {retries}/{max_retries}): {e}; waiting {current_wait}s")
            time.sleep(current_wait)
        except openai.APIConnectionError as e:
            retries += 1
            print(f"API connection error (retry {retries}/{max_retries}): {e}; waiting {current_wait}s")
            time.sleep(current_wait)
        except openai.RateLimitError as e:
            retries += 1
            print(f"Rate limit (retry {retries}/{max_retries}): {e}; waiting {current_wait}s")
            time.sleep(current_wait)
        except openai.APIStatusError as e:
            retries += 1
            print(f"API status error (retry {retries}/{max_retries}): {e}; waiting {current_wait}s")
            time.sleep(current_wait)

    if completion is None:
        raise RuntimeError(f"Failed after {max_retries} retries for model={model}")

    message = completion.choices[0].message
    content = message.content
    if content is None or (isinstance(content, str) and not content.strip()):
        # Some Ark reasoning models return only reasoning_content when
        # max_tokens is too small; surface that instead of a silent empty string.
        extra = getattr(message, "model_extra", None) or {}
        reasoning = extra.get("reasoning_content") if isinstance(extra, dict) else None
        if not reasoning and hasattr(message, "model_dump"):
            reasoning = (message.model_dump() or {}).get("reasoning_content")
        if reasoning:
            raise RuntimeError(
                f"Empty content for model={actual_model}; reasoning_tokens likely "
                f"consumed max_tokens={num_tokens_request}. Raise num_tokens_request."
            )
        return content or ""
    return content


def run_chatgpt_with_examples(query, examples, input, num_gen=1, num_tokens_request=1000, use_16k=False, wait_time=1, temperature=1.0, model=None):

    client = _get_openai_client()
    completion = None

    messages = [{"role": "system", "content": query}]
    for inp, out in examples:
        messages.append({"role": "user", "content": inp})
        messages.append({"role": "assistant", "content": out})
    messages.append({"role": "user", "content": input})

    while completion is None:
        wait_time = wait_time * 2
        try:
            completion = client.chat.completions.create(
                model=get_default_openai_model() if model is None else model,
                temperature=temperature,
                max_tokens=num_tokens_request,
                n=num_gen,
                messages=messages
            )
        except openai.APIError as e:
            print(f"OpenAI API returned an API Error: {e}; waiting for {wait_time} seconds")
            time.sleep(wait_time)
        except openai.APIConnectionError as e:
            print(f"Failed to connect to OpenAI API: {e}; waiting for {wait_time} seconds")
            time.sleep(wait_time)
        except openai.RateLimitError as e:
            print(f"OpenAI API request exceeded rate limit: {e}")
        except openai.APIStatusError as e:
            print(f"OpenAI API status error: {e}; waiting for {wait_time} seconds")
            time.sleep(wait_time)

    return completion.choices[0].message.content
