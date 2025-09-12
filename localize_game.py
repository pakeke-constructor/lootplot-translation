
import requests
import re
import json
import os
from dotenv import load_dotenv

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


assert load_dotenv()


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
    if isinstance(data, dict) and 'string' in data and 'placeholders' in data:
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
TARGET_LANGUAGE = "Simplified Chinese"

KEYS = ""

def load_keywords():
    global KEYS
    with open("keywords.json") as f:
        dic = json.load(f)
        for k,v in dic.items():
            KEYS = "\n" + k + ": " + v
        KEYS += "\n"



PROMPT = f'''

You are an expert translator translating a strategy-game from English to {TARGET_LANGUAGE}.

The purpose of the game is to earn money, buy items, gain more points

The text will come with tags, eg: "[1]Lorem[/1] ipsum"
You should seek to keep the tags around the words as much as possible.  

Example input:
"[1]Hello[/1], I am [2]a [3]school teacher[/3][/2]"

Ideal output: (for Chinese)
[1]你好[/1]，我是[2]一名[3]学校老师[/3][/2]


If unsure, maintain the tags around the words.
Example:
"[1]Hello[/1] was said by me." --> "I said [1]hello[/1]"


There are also "keywords" that must be translated consistently.  
Here are the keywords that must be consistently translated:

{KEYS}



'''


#
# what LLM is best to use???
#
#  gpt-4o is apparently the best for short text.
#  Claude-3.5-sonnet was allegedly the best for coherence and flow though.
#  (deepseek good for chinese apparently?)
#
#


def chat(message, model="openai/gpt-3.5-turbo"):
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": message}]
        }
    )
    return response.json()["choices"][0]["message"]["content"]


