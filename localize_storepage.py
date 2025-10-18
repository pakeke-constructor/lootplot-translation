
import requests
import time
import httpx
import re
import textwrap
import json
import os

from dotenv import load_dotenv

from util import *

assert load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")





#
# what LLM is best to use???
#
#  gpt-4o is apparently the best for short text.
#  Claude-3.5-sonnet was allegedly the best for coherence and flow though.
#  (deepseek good for chinese apparently?)
#

MODEL = "openai/gpt-4o"
# MODEL = "claude/3.5-sonnet"


def translate_text(lang:str, text:str):
    langname = LANGUAGE_NAMES[lang]

    prompt = textwrap.dedent(f'''
    # ROLE AND GOAL
    You are an expert localization specialist, translating a strategy game from English to {langname}. Your primary goal is to produce translations that are extremely clear, concise, and natural-sounding for gamers. The game revolves around earning money, buying items, and gaining points.

    # CRITICAL RULES
    Follow these rules without exception:
    3.  **Prioritize Clarity & Brevity:** Your translations are for game UI elements and notifications. They MUST be concise and immediately understandable.
        * Sacrifice literal, word-for-word translation for clarity.
        * Sacrifice grammatical complexity for punchy, direct language.
        * This is the most important rule after keyword and tag handling.

    4.  **Output Format:** Your ONLY output must be the raw translated text. No explanations, apologies, or conversational text like "Here is the translation:".

    # TRANSLATION TASK

    Translate the following text to **{langname}**.

    **Source Text:** "{text}"
    ''')

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}]
    }

    backoff = 1
    for _ in range(5):
        try:
            with httpx.Client() as client:
                resp = client.post(url, headers=headers, json=data)
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
        except httpx.HTTPError:
            time.sleep(backoff)
            backoff *= 2
    raise Exception("Failed after 5 attempts")



def run(lang):
    jsn = NDict.from_file("input/storepage_english.json")
    OUT_FILE = f"output/storepage/{lang}.json"
    out_jsn = NDict.from_file(OUT_FILE)

    def loc(key: tuple,val: str)->str:
        x = out_jsn.get(key)
        if x:
            print("SKIPPING.")
            return x
        return translate_text(lang, val)

    jsn = jsn.map(loc, print_progress=True)

    jsn.to_file(OUT_FILE)

    


run("ru")

print("\n\n\n")

run("zh")




