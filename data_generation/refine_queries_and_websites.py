"""This is for refining ddg search results. trim the ones that are less relevant to the query"""
import os
import json
from openai import OpenAI
from pydantic import BaseModel
from typing import List
from multiprocessing import Pool

from prompts import (
    SYSTEM_PROMPT_REFINE_SEARCH_RESULTS,
    USER_PROMPT_REFINE_SEARCH_RESULTS
)


ORIGINAL_DIR = "./websites"
NEW_DIR = "./refined_websites"

if not os.path.isdir(NEW_DIR):
    os.makedirs(NEW_DIR)

client = OpenAI()


class Website(BaseModel):
    url: str
    title: str


class RefinementFormat(BaseModel):
    relevant_websites: List[Website]


def _refine_helper(query, websites):
    completion = client.chat.completions.parse(
        model="gpt-5",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_REFINE_SEARCH_RESULTS},
            {"role": "user", "content": USER_PROMPT_REFINE_SEARCH_RESULTS.format(query, websites)},
        ],
        response_format=RefinementFormat,
    )

    title_website_mapping = dict()
    for obj in websites:
        title_website_mapping[obj['title']] = obj['url']

    retained_websites = completion.choices[0].message.parsed.relevant_websites
    ret = list()
    for obj in retained_websites:
        if obj.title not in title_website_mapping:
            # something wrong, ignore result
            continue
        ret.append({"url": title_website_mapping[obj.title], "title": obj.title})
    return ret


def refine_query_websites(fname):
    with open(os.path.join(ORIGINAL_DIR, fname)) as f:
        query_website_records = json.load(f)

    ret = dict()
    for query, websites in query_website_records.items():
        if not websites:
            ret[query] = []
            continue
        ret[query] = _refine_helper(query, websites)

    with open(os.path.join(NEW_DIR, fname), "w") as f:
        json.dump(ret, f, indent=2)


def main():
    file_names = sorted([fname for fname in os.listdir(ORIGINAL_DIR) if fname.endswith("json")])
    with Pool(len(file_names)) as p:
        _ = p.map(refine_query_websites, file_names)


if __name__ == "__main__":
    main()

