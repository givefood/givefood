#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import logging

import requests
from time import sleep

from google import genai
from google.genai import types
from google.genai.errors import ServerError
from mistralai import Mistral

from givefood.utils.cache import get_cred


def gemini(prompt, temperature, response_mime_type = "application/json", response_schema = None, model = "gemini-2.5-flash"):
    """Send a prompt to Google Gemini and return the parsed response."""
    client = genai.Client(api_key = get_cred("gemini_api_key"))

    config = types.GenerateContentConfig(
        temperature = temperature,
        response_mime_type = response_mime_type,
        response_schema = response_schema,
        thinking_config = types.ThinkingConfig(thinking_budget = 0),
        safety_settings = [
            types.SafetySetting(
                category = types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold = types.HarmBlockThreshold.BLOCK_NONE,
            ),
            types.SafetySetting(
                category = types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold = types.HarmBlockThreshold.BLOCK_NONE,
            ),
            types.SafetySetting(
                category = types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold = types.HarmBlockThreshold.BLOCK_NONE,
            ),
            types.SafetySetting(
                category = types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold = types.HarmBlockThreshold.BLOCK_NONE,
            ),
        ]
    )

    try:
        response = client.models.generate_content(
            model = model,
            contents = [prompt],
            config = config,
        )
    except ServerError:
        sleep(60)
        response = client.models.generate_content(
            model = model,
            contents = [prompt],
            config = config,
        )
    return response.parsed


def mistral(prompt, temperature, response_format = "json_object", model = "open-mistral-nemo"):
    """Send a prompt to the Mistral AI API and return the response content."""
    client = Mistral(api_key = get_cred("mistral"))

    response = client.chat.complete(
        model = model,
        messages = [
            {"role": "user", "content": prompt}
        ],
        temperature = temperature,
        response_format = {"type": response_format},
    )

    content = response.choices[0].message.content

    if response_format == "json_object":
        return json.loads(content)

    return content


def openrouter(prompt, temperature, model, response_schema = None, cred_name = "openrouter_needtestbed"):
    """Send a prompt to the OpenRouter API and return the raw response."""
    key = get_cred(cred_name)

    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
    }

    if response_schema:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "response",
                "strict": True,
                "schema": response_schema,
            }
        }

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers = {
            "Authorization": "Bearer %s" % key,
            "Content-Type": "application/json",
        },
        json = payload,
        timeout = 60,
    )

    return response
