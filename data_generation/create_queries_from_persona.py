import os
import json
from openai import OpenAI
from pydantic import BaseModel
from typing import List
from multiprocessing import Pool

from prompts import SYSTEM_PROMPT_QUERIES_FROM_PERSONA, USER_PROMPT_QUERIES_FROM_PERSONA


PERSONA_DIR = "./persona_data"
QUERY_DIR = "./queries"

client = OpenAI()


class QueryFormat(BaseModel):
    queries: List[str]


def create_queries(file_name):
    with open(os.path.join(PERSONA_DIR, file_name)) as f:
        persona = json.load(f)

    completion = client.chat.completions.parse(
        model="gpt-5",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_QUERIES_FROM_PERSONA},
            {"role": "user", "content": USER_PROMPT_QUERIES_FROM_PERSONA.format(persona)},
        ],
        response_format=QueryFormat,
    )

    ret = completion.choices[0].message.parsed
    return ret


def write_queries(results, persona_files):
    if not os.path.isdir(QUERY_DIR):
        os.makedirs(QUERY_DIR)

    for fname, res in zip(persona_files, results):
        with open(os.path.join(QUERY_DIR, fname), "w") as f:
            json.dump(res.queries, f, indent=2)


def main():
    persona_files = [fname for fname in os.listdir(PERSONA_DIR) if fname.endswith("json")]

    with Pool(len(persona_files)) as p:
        results = p.map(create_queries, persona_files)

    write_queries(results, persona_files)


if __name__ == "__main__":
    main()

