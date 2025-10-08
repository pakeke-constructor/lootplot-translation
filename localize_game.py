
import requests
import time
import httpx
import re
import json
import os

from dotenv import load_dotenv

from util import *

assert load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")




def extract_tags_for_translation(text):
    """Extract custom tags and replace with numbered placeholders."""
    pattern = r'\{[^}]*\}'
    matches = re.findall(pattern, text)
    
    placeholders = {}
    clean_string = text
    tag_counter = 1
    
    for match in matches:
        if match.startswith('{/'):
            # Find the corresponding opening tag number
            opening_content = match[2:-1]  # Remove {/ and }
            opening_tag = None
            for placeholder, original in placeholders.items():
                if original == '{' + opening_content + '}' and not placeholder.startswith('[/'):
                    opening_tag = placeholder[1:-1]  # Get number from [1]
                    break
            
            if opening_tag:
                placeholder = f"[/{opening_tag}]"
            else:
                placeholder = f"[/{tag_counter}]"
                tag_counter += 1
        else:
            placeholder = f"[{tag_counter}]"
            tag_counter += 1
        
        placeholders[placeholder] = match
        clean_string = clean_string.replace(match, placeholder, 1)
    
    return {
        'string': clean_string,
        'placeholders': placeholders
    }


def json_to_translator_format(data):
    """Convert JSON with custom tags to translator-friendly format."""
    if isinstance(data, str):
        return extract_tags_for_translation(data)
    elif isinstance(data, dict):
        return {key: json_to_translator_format(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [json_to_translator_format(item) for item in data]
    else:
        return data

def json_from_translator_format(data):
    """Convert translator-friendly format back to original JSON with tags."""
    if isinstance(data, dict) and 'string' in data:
        result = data['string']
        for placeholder, original_tag in data['placeholders'].items():
            result = result.replace(placeholder, original_tag)
        return result
    elif isinstance(data, dict):
        return {key: json_from_translator_format(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [json_from_translator_format(item) for item in data]
    else:
        return data




TARGET_LANGUAGE_CODE = "zh"
TARGET_LANGUAGE = "Chinese Simplified"

KEYS = ""

def load_keywords():
    global KEYS
    assert not KEYS
    with open("keywords.json","r", encoding="utf8") as f:
        dic = json.loads(f.read())
        keywords = dic[TARGET_LANGUAGE_CODE]
        for k,v in dic["en"].items():
            assert k in keywords, "Target language is missing keyword: " + k

        for k,v in keywords.items():
            KEYS += "\n    " + k + ": " + v
        KEYS += "\n"


load_keywords()


#
# what LLM is best to use???
#
#  gpt-4o is apparently the best for short text.
#  Claude-3.5-sonnet was allegedly the best for coherence and flow though.
#  (deepseek good for chinese apparently?)
#

# MODEL = "openai/gpt-3.5-turbo"
MODEL = "openai/gpt-4o"


def translate_text(text):
    prompt = f'''
    # ROLE AND GOAL
    You are an expert localization specialist, translating a strategy game from English to {TARGET_LANGUAGE}. Your primary goal is to produce translations that are extremely clear, concise, and natural-sounding for gamers. The game revolves around earning money, buying items, and gaining points.

    # CRITICAL RULES
    Follow these rules without exception:

    1.  **Preserve Tags:** The source text contains formatting tags like `[1]...[/1]`. These tags must be preserved and wrap the corresponding words or phrases in the translated text. The meaning within the tags must be the same.
        * **Input Example:** `I will give you [1]three gold coins[/1].`
        * **Correct Output (Spanish):** `Te daré [1]tres monedas de oro[/1].`
        * **Incorrect Output:** `[1]Te daré[/1] tres monedas de oro.`

    2.  **Mandatory Keywords:** Below is a list of keywords. These keywords MUST be translated exactly as specified in the list below, regardless of context or casing in the source text. This rule overrides all other grammatical or stylistic considerations.
    {KEYS}

    3.  **Prioritize Clarity & Brevity:** Your translations are for game UI elements and notifications. They MUST be concise and immediately understandable.
        * Sacrifice literal, word-for-word translation for clarity.
        * Sacrifice grammatical complexity for punchy, direct language.
        * This is the most important rule after keyword and tag handling.

    4.  **Output Format:** Your ONLY output must be the raw translated text. No explanations, apologies, or conversational text like "Here is the translation:".

    # TRANSLATION TASK

    Translate the following text to **{TARGET_LANGUAGE}**.

    **Source Text:** "{text}"
    '''
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




def translate_text_umgcore(text):
    prompt = f'''
    # ROLE AND GOAL
    You are an expert localization specialist, translating a strategy game from English to {TARGET_LANGUAGE}. Your primary goal is to produce translations that are extremely clear, concise, and natural-sounding for gamers. The game revolves around earning money, buying items, and gaining points.

    # CRITICAL RULES
    Follow these rules without exception:

    1.  **Prioritize Clarity & Brevity:** Your translations are for game UI elements and notifications. They MUST be concise and immediately understandable.
        * If a singular word is provided as input, ONLY TRANSLATE THAT SINGULAR WORD.
        * Maintain punctuation and capitalization if possible.

    2.  **Output Format:** Your ONLY output must be the raw translated text. No explanations, apologies, or conversational text like "Here is the translation:".

    # TRANSLATION TASK

    Translate the following text to **{TARGET_LANGUAGE}**.

    **Source Text:** "{text}"
    '''
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
    jsn = read_json("input/localization_umgcore.json")

    out_jsn = map_dict(jsn, translate_text_umgcore, should_ignore_key=False, print_progress=True)

    write_json(f"output/game_umgcore/{lang}.json", out_jsn)






def fix(lang):
    jsn = NDict.from_file(f"output/game_mods/{lang}.json")

    def find_brac(text):
        matches = re.findall(r'\{([^}]*)\}', text)
        if len(matches) == 1:
            return matches[0]
        else:
            return False


    def fix_floating_tags(tupkey, val) -> str:
        key=tupkey[-1]
        if (not find_brac(key)):
            # no bracket; therefore, shouldnt have any [1], [/1]
            if re.match(r'\[/?\d\]', val):
                print("CLEANING: ", val)
                return re.sub(r'\[/?\d\]', '', val)
        return key


    # fix floating tags
    jsn = jsn.map(fix_floating_tags, None, False)

    # jsn.to_file(f"output/game_umgcore/{lang}.json")



fix("zh")

# run()




