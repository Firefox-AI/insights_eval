import os
import json
import random
import numpy as np
import pandas as pd
import argparse
from multiprocessing import Process
from collections import Counter

random.seed(2025)
np.random.seed(2025)

START_TIME = 1760720236895000
END_TIME = 1765907836895000

with open("./data/query_labels.json") as f:
    QUERY_LABELS = json.load(f)

with open("./data/url_labels.json") as f:
    URL_LABELS = json.load(f)

SEARCH_ENGINE_DOMAINS = [
  "google",
  "bing",
  "duckduckgo",
  "search.brave",
  "yahoo",
  "startpage",
  "ecosia",
  "baidu",
  "yandex",
]


def _get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-records", dest="min_records", type=int, default=30)
    parser.add_argument("--max-records", dest="max_records", type=int, default=30)
    parser.add_argument("--bank-dir", dest="bank_dir", default="./websites", help="bank of all the query-website records")
    parser.add_argument("--persona-dir", dest="persona_dir", default="./persona_data", help="directory of all persona data")
    parser.add_argument("--output-dir", dest="output_dir", default="./records", help="output directory")
    args = parser.parse_args()

    if not os.path.isdir(args.output_dir):
        os.makedirs(args.output_dir)

    return args


def _insert_query(records, query):
    domain = random.sample(SEARCH_ENGINE_DOMAINS, 1)[0]
    converted_query = query.replace(" ", "+")
    url = f"https://{domain}.com/search?q={converted_query}"
    host = f"{domain}.com"
    title = f"{domain.capitalize()} Search : {query}"
    category, intent = QUERY_LABELS[query]['labels']
    records.append([url, host, title, 0, category, intent])


def _insert_websites(records, selected_websites):
    elapse = 0
    for website in selected_websites:
        title = website['title']
        url = website['url']
        second_half = url.split("//")[1]
        host = second_half.split("/")[0]
        elapse += random.randint(10000000, 120000000) # 10~120 seconds
        category, intent = URL_LABELS[url]['labels']
        records.append([url, host, title, elapse, category, intent])


def randomly_insert_records(records, available_queries, query_websites):
    query = random.sample(available_queries, 1)[0]
    _insert_query(records, query)

    website_set = query_websites[query]
    if not website_set:
        return

    num = random.randint(1, len(website_set))
    selected_websites = random.sample(website_set, num)
    _insert_websites(records, selected_websites)


def post_process_visit_date(records):
    # figure out max elapse
    elapses = [obj[3] for obj in records]
    max_elapse = max(elapses)
    _max = END_TIME - max_elapse

    num_queries = elapses.count(0)
    query_times = sorted(np.random.randint(START_TIME, _max, num_queries).tolist())
    for obj in records:
        if obj[3] == 0:
            base = query_times.pop(0)
            obj[3] += base
        else:
            obj[3] += base


def assign_frec_pct(records):
    frec_dict = get_frec_dict([obj[0] for obj in records])
    for obj in records:
        obj.append(frec_dict[obj[0]])


def assign_domain_frec_pct(records):
    frec_dict = get_frec_dict([obj[1] for obj in records])
    for obj in records:
        obj.append(frec_dict[obj[1]])


def normalize_to_range(values, new_min=20, new_max=100):
    """
    Normalize a list of floats to a given range [new_min, new_max].

    Args:
        values (list of float): Input numbers.
        new_min (float): Lower bound of the new range (default=20).
        new_max (float): Upper bound of the new range (default=100).

    Returns:
        list of float: Normalized numbers scaled to [new_min, new_max].
    """
    if not values:
        return []

    min_val = min(values)
    max_val = max(values)

    if max_val == min_val:
        # Avoid divide-by-zero; all values are the same
        mid = (new_max + new_min) / 2
        return [mid for _ in values]

    return [
        ((v - min_val) / (max_val - min_val)) * (new_max - new_min) + new_min
        for v in values
    ]



def get_frec_dict(arr):
    freq_dict = dict()
    recency_dict = dict()
    for idx, text in enumerate(arr):
        freq_dict[text] = freq_dict.get(text, 0) + 1
        if text not in recency_dict:
            recency_dict[text] = list()
        recency_dict[text].append(idx)

    freq_arr = [freq_dict[text] for text in arr]
    rec_arr = [sum(recency_dict[text]) for text in arr]
    freq_arr = normalize_to_range(freq_arr)
    rec_arr = normalize_to_range(rec_arr)

    recency = [(x + y) / 2 for x, y in zip(freq_arr, rec_arr)]
    return dict(zip(arr, recency))


def build_intermediate_profile(fname, args):
    """
    url | host | title | category | intent | visit_date | frecency_pct | domain_frecency_pct
    visit_date ~= 1765400059075515
    """
    with open(os.path.join(args.persona_dir, fname)) as f:
        persona_data = json.load(f)

    with open(os.path.join(args.bank_dir, fname)) as f:
        query_websites = json.load(f)

    available_queries = list(query_websites.keys())

    limit = random.randint(args.min_records, args.max_records+1)
    records = list()

    while len(records) < limit:
        randomly_insert_records(records, available_queries, query_websites)

    records = records[:limit]

    post_process_visit_date(records)
    assign_frec_pct(records)
    assign_domain_frec_pct(records)

    columns = ['url', 'host', 'title', 'visit_date', 'category', 'intent', 'frecency_pct', 'domain_frecency_pct']
    df = pd.DataFrame(columns=columns, data=records)
    df.to_csv(os.path.join(args.output_dir, fname[:-4] + "csv"), index=False)


def main():
    args = _get_args()
    file_names = sorted(os.listdir(args.persona_dir))
    process_list = [
        Process(target=build_intermediate_profile, args=(fname, args)) for fname in file_names
    ]

    for p in process_list:
        p.start()
    for p in process_list:
        p.join()

    print("ALL DONE!!!")


if __name__ == "__main__":
    main()

