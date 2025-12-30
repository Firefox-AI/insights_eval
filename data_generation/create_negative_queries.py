import os
import json
from openai import OpenAI
from pydantic import BaseModel
from typing import List
from multiprocessing import Pool

from prompts import SYSTEM_PROMPT_NEGATIVE_QUERIES, USER_PROMPT_NEGATIVE_QUERIES


PERSONA_DIR = "./data/persona_data"
QUERY_DIR = "./data/negative_queries"

client = OpenAI()


class QueryFormat(BaseModel):
    """Format for query generation output."""
    queries: List[str]


def create_negative_queries(file_name):
    """Generate 10 sensitive queries for a given persona.
    
    Args:
        file_name: Name of the persona JSON file.
        
    Returns:
        QueryFormat object with list of 10 sensitive query strings.
    """
    with open(os.path.join(PERSONA_DIR, file_name)) as f:
        persona = json.load(f)

    user_prompt = USER_PROMPT_NEGATIVE_QUERIES.format(
        persona.get('name', ''),
        persona.get('description', ''),
        '\n'.join(persona.get('example_behaviours', []))
    )

    completion = client.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_NEGATIVE_QUERIES},
            {"role": "user", "content": user_prompt},
        ],
        response_format=QueryFormat,
    )

    ret = completion.choices[0].message.parsed
    return ret


def write_queries(results, persona_files):
    """Write generated queries to JSON files.
    
    Args:
        results: List of QueryFormat objects.
        persona_files: List of persona file names.
    """
    if not os.path.isdir(QUERY_DIR):
        os.makedirs(QUERY_DIR)

    for fname, res in zip(persona_files, results):
        with open(os.path.join(QUERY_DIR, fname), "w") as f:
            json.dump(res.queries, f, indent=2)


def main():
    """Main execution function."""
    persona_files = sorted([
        fname for fname in os.listdir(PERSONA_DIR) 
        if fname.endswith("json")
    ])

    with Pool(len(persona_files)) as p:
        results = p.map(create_negative_queries, persona_files)

    write_queries(results, persona_files)
    print(f"Saved to {QUERY_DIR}/")


if __name__ == "__main__":
    main()
