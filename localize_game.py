
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
    def extract_tag_name(tag):
        content = tag[1:-1]
        if content.startswith('/'):
            content = content[1:]
        return content.split()[0] if content else ''


    def is_closing_tag(tag):
        return tag.startswith('{/')

    pattern = r'\{[^}]*\}'
    matches = re.findall(pattern, text)
    
    placeholders = {}
    clean_string = text
    tag_counter = 1
    
    tag_name_to_number = {}
    opening_tags_seen = set()
    
    for match in matches:
        if is_closing_tag(match):
            tag_name = extract_tag_name(match)
            
            if tag_name in tag_name_to_number:
                number = tag_name_to_number[tag_name]
                placeholder = f"[/{number}]"
            else:
                placeholder = f"[/{tag_counter}]"
                tag_counter += 1
        else:
            tag_name = extract_tag_name(match)
            number = tag_counter
            placeholder = f"[{number}]"
            
            tag_name_to_number[tag_name] = number
            opening_tags_seen.add(tag_name)
            
            tag_counter += 1
        
        placeholders[placeholder] = match
        clean_string = clean_string.replace(match, placeholder, 1)
    
    for tag_name in opening_tags_seen:
        number = tag_name_to_number[tag_name]
        closing_placeholder = f"[/{number}]"
        
        if closing_placeholder not in placeholders:
            placeholders[closing_placeholder] = f"{{/{tag_name}}}"
    
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
        if len(matches) >= 1:
            return True
        else:
            return False


    def fix_floating_tags(tupkey, val) -> str:
        key=tupkey[-1]
        if (not find_brac(key)):
            # no bracket; therefore, shouldnt have any [1], [/1]
            if re.match(r'\[/?\d\]', val):
                print("FOUND: ", val)
                return val
                return re.sub(r'\[/?\d\]', '', val)
        return val


    # fix floating tags
    jsn = jsn.map(fix_floating_tags, None, False)

    # jsn.to_file(f"output/game_umgcore/{lang}.json")



# fix("ru")

# run()



# Test Cases
def test_general_case():
    """Test basic opening and closing tags."""
    text = "blah {foo}FOOBAR{/foo}"
    result = extract_tags_for_translation(text)
    
    print("Test: General case")
    print(f"Input:  {text}")
    print(f"Output: {result['string']}")
    print(f"Placeholders: {result['placeholders']}")
    
    assert result['string'] == "blah [1]FOOBAR[/1]"
    assert result['placeholders']['[1]'] == '{foo}'
    assert result['placeholders']['[/1]'] == '{/foo}'
    print("✓ Passed\n")


def test_nested_tags():
    """Test nested tags with same name."""
    text = "{bar}blah {foo}FOOBAR{/foo}{/bar}"
    result = extract_tags_for_translation(text)
    
    print("Test: Nested tags")
    print(f"Input:  {text}")
    print(f"Output: {result['string']}")
    print(f"Placeholders: {result['placeholders']}")
    
    assert result['string'] == "[1]blah [2]FOOBAR[/2][/1]"
    assert result['placeholders']['[1]'] == '{bar}'
    assert result['placeholders']['[2]'] == '{foo}'
    assert result['placeholders']['[/1]'] == '{/bar}'
    assert result['placeholders']['[/2]'] == '{/foo}'
    print("✓ Passed\n")


def test_tags_with_arguments():
    """Test tags with arguments."""
    text = "text {c r=0 g=0 b=1}blue text!{/c}"
    result = extract_tags_for_translation(text)
    
    print("Test: Tags with arguments")
    print(f"Input:  {text}")
    print(f"Output: {result['string']}")
    print(f"Placeholders: {result['placeholders']}")
    
    assert result['string'] == "text [1]blue text![/1]"
    assert result['placeholders']['[1]'] == '{c r=0 g=0 b=1}'
    assert result['placeholders']['[/1]'] == '{/c}'
    print("✓ Passed\n")


def test_missing_closing_tag():
    """Test automatic closing tag generation."""
    text = "{foo}hello!"
    result = extract_tags_for_translation(text)
    
    print("Test: Missing closing tag")
    print(f"Input:  {text}")
    print(f"Output: {result['string']}")
    print(f"Placeholders: {result['placeholders']}")
    
    assert result['string'] == "[1]hello!"
    assert result['placeholders']['[1]'] == '{foo}'
    assert result['placeholders']['[/1]'] == '{/foo}'
    print("✓ Passed\n")


def test_multiple_same_tag_different_args():
    """Test multiple instances of same tag with different arguments."""
    text = "{c r=255}red{/c} and {c g=255}green{/c} and {c b=255}blue{/c}"
    result = extract_tags_for_translation(text)
    
    print("Test: Multiple same tags with different arguments")
    print(f"Input:  {text}")
    print(f"Output: {result['string']}")
    print(f"Placeholders: {result['placeholders']}")
    
    assert result['string'] == "[1]red[/1] and [2]green[/2] and [3]blue[/3]"
    assert result['placeholders']['[1]'] == '{c r=255}'
    assert result['placeholders']['[2]'] == '{c g=255}'
    assert result['placeholders']['[3]'] == '{c b=255}'
    assert result['placeholders']['[/1]'] == '{/c}'
    assert result['placeholders']['[/2]'] == '{/c}'
    assert result['placeholders']['[/3]'] == '{/c}'
    print("✓ Passed\n")


def test_nested_different_tags_with_args():
    """Test nested tags with different names and arguments."""
    text = "{b}bold {c r=255}red bold{/c} still bold{/b}"
    result = extract_tags_for_translation(text)
    
    print("Test: Nested different tags with arguments")
    print(f"Input:  {text}")
    print(f"Output: {result['string']}")
    print(f"Placeholders: {result['placeholders']}")
    
    assert result['string'] == "[1]bold [2]red bold[/2] still bold[/1]"
    assert result['placeholders']['[1]'] == '{b}'
    assert result['placeholders']['[2]'] == '{c r=255}'
    assert result['placeholders']['[/1]'] == '{/b}'
    assert result['placeholders']['[/2]'] == '{/c}'
    print("✓ Passed\n")


def test_many_tags_sprawled():
    """Test complex text with multiple different tags sprawled throughout."""
    text = (
        "Welcome {b}brave{/b} adventurer! "
        "You found {c r=255 g=215 b=0}golden coins{/c} and "
        "{i}mysterious{/i} artifacts. "
        "{u}Warning:{/u} {c r=255 g=0 b=0}danger{/c} ahead! "
        "Use {b}{i}extreme caution{/i}{/b} always."
    )
    result = extract_tags_for_translation(text)
    
    print("Test: Many tags sprawled out")
    print(f"Input:  {text}")
    print(f"Output: {result['string']}")
    print(f"Placeholders: {result['placeholders']}")
    
    expected_string = (
        "Welcome [1]brave[/1] adventurer! "
        "You found [2]golden coins[/2] and "
        "[3]mysterious[/3] artifacts. "
        "[4]Warning:[/4] [5]danger[/5] ahead! "
        "Use [6][7]extreme caution[/7][/6] always."
    )
    
    assert result['string'] == expected_string
    assert result['placeholders']['[1]'] == '{b}'
    assert result['placeholders']['[2]'] == '{c r=255 g=215 b=0}'
    assert result['placeholders']['[3]'] == '{i}'
    assert result['placeholders']['[4]'] == '{u}'
    assert result['placeholders']['[5]'] == '{c r=255 g=0 b=0}'
    assert result['placeholders']['[6]'] == '{b}'
    assert result['placeholders']['[7]'] == '{i}'
    print("✓ Passed\n")


def test_edge_case_only_closing_tag():
    """Test edge case with only closing tag (no matching opening)."""
    text = "some text {/foo} here"
    result = extract_tags_for_translation(text)
    
    print("Test: Edge case - only closing tag")
    print(f"Input:  {text}")
    print(f"Output: {result['string']}")
    print(f"Placeholders: {result['placeholders']}")
    
    assert result['string'] == "some text [/1] here"
    assert result['placeholders']['[/1]'] == '{/foo}'
    print("✓ Passed\n")


def test_empty_text():
    """Test with empty text."""
    text = ""
    result = extract_tags_for_translation(text)
    
    print("Test: Empty text")
    print(f"Input:  '{text}'")
    print(f"Output: '{result['string']}'")
    print(f"Placeholders: {result['placeholders']}")
    
    assert result['string'] == ""
    assert result['placeholders'] == {}
    print("✓ Passed\n")



def test_nested_args():
    """Test with text but no tags."""
    text = "test {c r=1 b=0}{c r=0}nesty{/c}{/c}"
    result = extract_tags_for_translation(text)
    
    print("Test: No tags")
    print(f"Input:  {text}")
    print(f"Output: {result['string']}")
    print(f"Placeholders: {result['placeholders']}")
    
    print("✓ Passed\n")


test_nested_args()

raise ValueError("x")




def test_no_tags():
    """Test with text but no tags."""
    text = "This is plain text with no tags"
    result = extract_tags_for_translation(text)
    
    print("Test: No tags")
    print(f"Input:  {text}")
    print(f"Output: {result['string']}")
    print(f"Placeholders: {result['placeholders']}")
    
    assert result['string'] == text
    assert result['placeholders'] == {}
    print("✓ Passed\n")


# Run all tests
if __name__ == "__main__":
    print("=" * 60)
    print("Running Tag Extraction Tests")
    print("=" * 60 + "\n")
    
    # test_general_case()
    test_many_tags_sprawled()
    test_nested_tags()
    test_tags_with_arguments()
    test_missing_closing_tag()
    test_multiple_same_tag_different_args()
    test_nested_different_tags_with_args()
    test_edge_case_only_closing_tag()
    test_empty_text()
    test_no_tags()
    
    print("=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)

