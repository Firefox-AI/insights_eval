"""Convert queries and website history into records and label category / intent"""
import os
import json
from openai import OpenAI
from pydantic import BaseModel
from typing import List
from multiprocessing import Pool

from utils import batch_generator
from prompts import (
    SYSTEM_PROMPT_LABEL_QUERY,
    USER_PROMPT_LABEL_QUERY,
    SYSTEM_PROMPT_LABEL_WEBSITE,
    USER_PROMPT_LABEL_WEBSITE
)


QUERY_WEBSITE_DIR = "./websites"
OUTPUT_DIR = "./data"
QUERY_LABEL_FILE = "query_labels.json"
URL_LABEL_FILE = "url_labels.json"
BATCH_SIZE = 200


if not os.path.isdir(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

client = OpenAI()


class LabelFormat(BaseModel):
    category_intent: List[str]


def label_query(query):
    completion = client.chat.completions.parse(
        model="gpt-5",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_LABEL_QUERY},
            {"role": "user", "content": USER_PROMPT_LABEL_QUERY.format(query)},
        ],
        response_format=LabelFormat,
    )

    ret = completion.choices[0].message.parsed
    return ret.category_intent


def label_website(website):
    completion = client.chat.completions.parse(
        model="gpt-5",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_LABEL_WEBSITE},
            {"role": "user", "content": USER_PROMPT_LABEL_WEBSITE.format(website)},
        ],
        response_format=LabelFormat,
    )

    ret = completion.choices[0].message.parsed
    return ret.category_intent


def label_queries(query_dict):
    queries_to_label = list(query_dict.keys())
    finished_count = 0
    for batch in batch_generator(queries_to_label, BATCH_SIZE):

        with Pool(len(batch)) as p:
            results = p.map(label_query, batch)
        for query, labels in zip(batch, results):
            query_dict[query]['labels'] = labels
        finished_count += len(batch)
        print(f"Finished {finished_count} queries.")

    with open(os.path.join(OUTPUT_DIR, QUERY_LABEL_FILE), "w") as f:
        json.dump(query_dict, f, indent=2)


def label_urls(url_dict):
    websites_to_label = list(url_dict.values())
    finished_count = 0
    for batch in batch_generator(websites_to_label, BATCH_SIZE):
        with Pool(len(batch)) as p:
            results = p.map(label_website, batch)
        for website, labels in zip(batch, results):
            url_dict[website['url']]['labels'] = labels
        finished_count += len(batch)
        print(f"Finished {finished_count} websites.")

    with open(os.path.join(OUTPUT_DIR, URL_LABEL_FILE), "w") as f:
        json.dump(url_dict, f, indent=2)


def main():
    query_dict = dict()
    url_dict = dict()
    for fname in os.listdir(QUERY_WEBSITE_DIR):
        with open(os.path.join(QUERY_WEBSITE_DIR, fname)) as f:
            query_website_result = json.load(f)
        for query, website_arr in query_website_result.items():
            query_dict[query] = dict()
            for obj in website_arr:
                url_dict[obj['url']] = obj

    print(f"Got {len(query_dict)} queries and {len(url_dict)} websites to label...")
    label_queries(query_dict)
    print("Finished query labels")
    label_urls(url_dict)
    print("Finished website labels")


if __name__ == "__main__":
    main()

