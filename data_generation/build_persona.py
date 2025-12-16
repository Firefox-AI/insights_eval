import os
import json
import numpy as np
from openai import OpenAI
from pydantic import BaseModel
from typing import List
from multiprocessing import Pool

from prompts import SYSTEM_PROMPT_PERSONA_CREATION, USER_PROMPT_PERSONA_CREATION


PERSONA_DIR = "./persona_data"

with open("data/personas_base.json") as f:
    BASE_PERSONA = json.load(f)

NUM_PERSON = len(BASE_PERSONA)


class PersonaFormat(BaseModel):
    name: str
    persona_detail_description: str
    behaviour_or_hobby_instances: List[str]


client = OpenAI()


def create_complex_persona(id_arr):
    user_prompt = USER_PROMPT_PERSONA_CREATION
    for idx, _id in enumerate(id_arr):
        persona = BASE_PERSONA[_id]['persona_name']
        description = BASE_PERSONA[_id]['description']
        line = f"\n{idx+1}: persona = {persona}; description = {description}\n"
        user_prompt += line

    completion = client.chat.completions.parse(
        model="gpt-5",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_PERSONA_CREATION},
            {"role": "user", "content": user_prompt},
        ],
        response_format=PersonaFormat,
    )

    ret = completion.choices[0].message.parsed
    return ret


def write_persona_data(results):
    if not os.path.isdir(PERSONA_DIR):
        os.makedirs(PERSONA_DIR)

    seen_name = set()
    for idx, res in enumerate(results):
        name = res.name
        description = res.persona_detail_description
        instances = res.behaviour_or_hobby_instances
        name_id = name.replace(" ", "-")
        data = {"name": name, "description": description, "example_behaviours": instances}
        file_name = os.path.join(PERSONA_DIR, f"id_{idx}_{name_id}.json")
        with open(file_name, "w") as f:
            json.dump(data, f, indent=2)


def main():
    id_selections = [[idx] for idx in range(NUM_PERSON)]

    with Pool(len(id_selections)) as p:
        results = p.map(create_complex_persona, id_selections)

    write_persona_data(results)


if __name__ == "__main__":
    main()

