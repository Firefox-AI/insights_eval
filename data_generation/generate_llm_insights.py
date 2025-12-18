"""This is for refining ddg search results. trim the ones that are less relevant to the query"""
import os
import json
import pandas as pd
import argparse
from openai import OpenAI
from pydantic import BaseModel
from typing import List
from multiprocessing import Process

from prompts import (
    SYSTEM_PROMPT_GENERATE_INSIGHTS,
    USER_PROMPT_GENERATE_INSIGHTS
)


client = OpenAI()


class InsightBase(BaseModel):
    insight_summary: str
    category: str
    intent: str
    score: int


class InsightFormat(BaseModel):
    insights: List[InsightBase]


def _get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile-dir", dest="profile_dir", default="./records")
    parser.add_argument("--output-dir", dest="output_dir", default="./insights")
    args = parser.parse_args()

    if not os.path.isdir(args.output_dir):
        os.makedirs(args.output_dir)

    return args


def _convert_profile_string(df):
    records = list()
    for idx, row in df.iterrows():
        tmp = ""
        tmp += f"Record {idx+1}:\n\n"
        tmp += f"  URL: {row.url}\n"
        tmp += f"  host: {row.host}\n"
        tmp += f"  title: {row.title}\n"
        tmp += f"  visit_date: {row.visit_date}\n"
        tmp += f"  frecency_percenage: {row.frecency_pct}\n"
        tmp += f"  domain_frecency_percenage: {row.domain_frecency_pct}\n"
        records.append(tmp)

    ret = "\n".join(records)
    return ret


def generate_insights(fname, args):
    # read intermediates from csv files
    df = pd.read_csv(os.path.join(args.profile_dir, fname))
    first_id = fname.split("_")[1]

    profile_string = _convert_profile_string(df)

    completion = client.chat.completions.parse(
        model="gpt-5",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_GENERATE_INSIGHTS},
            {"role": "user", "content": USER_PROMPT_GENERATE_INSIGHTS.format(profile_string)},
        ],
        response_format=InsightFormat,
    )

    insights = [
        {
            "id": f"ins-{first_id:0>4}{idx:0>4}",
            "insight_summary": obj.insight_summary,
            "category": obj.category,
            "intent": obj.intent,
            "socre": obj.score,
            "updated_at": 1765907836895,
            "is_deleted": False

        }
        for idx, obj in enumerate(completion.choices[0].message.parsed.insights)
    ]

    ret = {
        "insights": insights,
        "meta": {"last_history_insight_ts": 1765907836895, "last_chat_insight_ts": 0},
        "version": 1
    }

    # write result into json files
    with open(os.path.join(args.output_dir, fname[:-3] + "json"), "w") as f:
        json.dump(ret, f, indent=2)


def main():
    args = _get_args()

    file_names = sorted([fname for fname in os.listdir(args.profile_dir) if fname.endswith("csv")])
    process_list = [
        Process(target=generate_insights, args=(fname, args)) for fname in file_names
    ]

    for p in process_list:
        p.start()
    for p in process_list:
        p.join()


if __name__ == "__main__":
    main()

