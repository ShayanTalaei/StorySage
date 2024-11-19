import re

def get_placeholders(prompt: str):
    return re.findall(r"\{(\w+)\}", prompt)

def format_prompt(prompt: str, key_values: dict):
    placeholders = get_placeholders(prompt)
    for placeholder in placeholders:
        if placeholder not in key_values:
            key_values[placeholder] = f"{{{placeholder}}}"
    return prompt.format(**key_values)
