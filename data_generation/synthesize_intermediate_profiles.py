import os
import json
import random
import numpy as np
import pandas as pd
import argparse
from multiprocessing import Process
from collections import Counter
from openai import OpenAI
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

random.seed(2025)
np.random.seed(2025)

client = OpenAI()

# 10 seconds
START_TIME = 1760720236895000
# 120 seconds
END_TIME = 1765907836895000

# Minimum websites a query must have to be included
MIN_WEBSITES_PER_QUERY = 3

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


class ProxyQueriesFormat(BaseModel):
    """Structured output format for proxy search queries."""
    queries: List[str]


def _generate_proxy_queries_from_titles(titles):
    """
    Generate natural search queries from website titles using GPT-5.
    
    Args:
        titles (list of str): Website titles to convert into search queries.
    
    Returns:
        list of str: Generated search query strings. Returns empty list if API call fails.
    """
    if not titles:
        return []
    
    try:
        titles_text = "\n".join([f"- {title}" for title in titles])
        prompt = f"""Given the following website titles, generate natural search queries that someone might have used to find these websites. Each query should be a short, natural phrase (2-5 words) that captures the main topic or intent.

Website titles:
{titles_text}

Generate one search query for each title."""
        
        completion = client.chat.completions.parse(
            model="gpt-5",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates natural search queries from website titles."},
                {"role": "user", "content": prompt},
            ],
            response_format=ProxyQueriesFormat,
        )
        
        result = completion.choices[0].message.parsed
        return result.queries if result else []
    except Exception as e:
        print(f"Warning: Failed to generate proxy queries: {e}")
        return []


def _get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-records", dest="min_records", type=int, default=30)
    parser.add_argument("--max-records", dest="max_records", type=int, default=30)
    parser.add_argument("--positive-bank-dir", dest="positive_bank_dir", default="./data/positive_websites", help="bank of positive query-website records")
    parser.add_argument("--negative-bank-dir", dest="negative_bank_dir", default="./data/negative_websites", help="bank of negative query-website records")
    parser.add_argument("--min-negative-pct", dest="min_negative_pct", type=float, default=5.0, help="minimum percentage of negative records")
    parser.add_argument("--max-negative-pct", dest="max_negative_pct", type=float, default=5.0, help="maximum percentage of negative records")
    parser.add_argument("--persona-dir", dest="persona_dir", default="./data/persona_data", help="directory of all persona data")
    parser.add_argument("--output-dir", dest="output_dir", default="./records", help="output directory")
    parser.add_argument("--min-proxy-queries", dest="min_proxy_queries", type=int, default=1, help="minimum number of proxy search queries to generate per group of websites")
    parser.add_argument("--max-proxy-queries", dest="max_proxy_queries", type=int, default=1, help="maximum number of proxy search queries to generate per group of websites")
    args = parser.parse_args()

    if not os.path.isdir(args.output_dir):
        os.makedirs(args.output_dir)

    return args


def _insert_query(records, query, is_negative=False):
    domain = random.sample(SEARCH_ENGINE_DOMAINS, 1)[0]
    converted_query = query.replace(" ", "+")
    url = f"https://{domain}.com/search?q={converted_query}"
    host = f"{domain}.com"
    title = f"{domain.capitalize()} Search : {query}"
    #category, intent = QUERY_LABELS[query]['labels']
    records.append([url, host, title, 0, is_negative]) #category, intent, is_negative])


def _insert_websites(records, selected_websites, is_negative=False):
    elapse = 0
    for website in selected_websites:
        title = website['title']
        url = website['url']
        second_half = url.split("//")[1]
        host = second_half.split("/")[0]
        elapse += random.randint(10000000, 120000000) # 10~120 seconds
        #category, intent = URL_LABELS[url]['labels']
        records.append([url, host, title, elapse, is_negative]) #category, intent, is_negative])


def randomly_insert_records(records, available_queries, query_websites, used_queries, is_negative=False, proxy_query_range=(1, 1)):
    """
    Randomly insert website records and proxy search queries into browsing history.
    
    Args:
        records (list): List to append records to.
        available_queries (set): Available search queries to choose from.
        query_websites (dict): Mapping of queries to their website sets.
        used_queries (set): Set to track used queries.
        is_negative (bool): Whether these are negative records.
        proxy_query_range (tuple): (min, max) number of proxy queries to generate.
    """
    query = random.choice(sorted(available_queries))

    # Randomly select between MIN_WEBSITES_PER_QUERY and len(website_set) websites for each query
    # If a query has fewer than MIN_WEBSITES_PER_QUERY websites, skip it
    # We need enough websites in each query to have sufficient evidence for a memory
    website_set = query_websites[query]
    num_websites = len(website_set)
    if num_websites <= MIN_WEBSITES_PER_QUERY:
        return
    num = random.randint(MIN_WEBSITES_PER_QUERY, len(website_set))
    selected_websites = random.sample(website_set, num)
    used_queries.add(query)

    # Generate and insert proxy search queries from website titles
    min_queries, max_queries = proxy_query_range
    if min_queries > 0 or max_queries > 0:
        titles = [website['title'] for website in selected_websites]
        generated_queries = _generate_proxy_queries_from_titles(titles)
        
        if generated_queries:
            num_proxy_queries = random.randint(min_queries, max_queries)
            num_proxy_queries = min(num_proxy_queries, len(generated_queries))
            
            if num_proxy_queries > 0:
                selected_proxy_queries = random.sample(generated_queries, num_proxy_queries)
                for proxy_query in selected_proxy_queries:
                    _insert_query(records, proxy_query, is_negative=is_negative)
    
    _insert_websites(records, selected_websites, is_negative=is_negative)


def post_process_visit_date(records):
    # figure out max elapse
    elapses = [obj[3] for obj in records]
    max_elapse = max(elapses)
    _max = END_TIME - max_elapse

    num_queries = elapses.count(0)
    query_times = sorted(np.random.randint(START_TIME, _max, num_queries).tolist())
    base = None
    for obj in records:
        if obj[3] == 0:
            base = query_times.pop(0)
            obj[3] = base
        else:
            if base is not None:
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
    url | host | title | category | intent | visit_date | frecency_pct | domain_frecency_pct | is_negative
    visit_date ~= 1765400059075515
    """

    # Load positive websites
    positive_file = os.path.join(args.positive_bank_dir, fname)
    negative_file = os.path.join(args.negative_bank_dir, fname)
    
    if not os.path.exists(positive_file):
        print(f"Warning: Positive file not found: {positive_file}")
        return
    
    with open(positive_file) as f:
        positive_query_websites = json.load(f)
    
    # Load negative websites
    negative_query_websites = {}
    if os.path.exists(negative_file):
        with open(negative_file) as f:
            negative_query_websites = json.load(f)
    
    # Get available queries for both
    positive_available_queries = set(positive_query_websites.keys())
    negative_available_queries = set(negative_query_websites.keys())
    
    used_positive_queries = set()
    used_negative_queries = set()

    # Calculate total records needed
    total_limit = random.randint(args.min_records, args.max_records + 1)
    
    # Calculate target negative percentage (random between min and max)
    negative_pct = random.uniform(args.min_negative_pct, args.max_negative_pct)
    target_negative_count = int(total_limit * (negative_pct / 100.0))
    target_positive_count = total_limit - target_negative_count
    
    positive_records = []
    negative_records = []

    # Insert positive records
    #last_len = -1
    #retries = 0
    while len(positive_records) < target_positive_count:
        randomly_insert_records(
            positive_records,
            positive_available_queries,
            positive_query_websites,
            used_positive_queries,
            is_negative=False,
            proxy_query_range=(args.min_proxy_queries, args.max_proxy_queries)
        )
        positive_available_queries -= used_positive_queries
        # if len(positive_records) > last_len:
        #     last_len = len(positive_records)
        #     retries = 0
        # else:
        #     retries += 1
        #     if retries >= 5:
        #         break
    
    # Insert negative records
    if negative_query_websites:
        last_len = -1
        retries = 0
        while len(negative_records) < target_negative_count:
            randomly_insert_records(
                negative_records, 
                negative_available_queries,
                negative_query_websites, 
                used_negative_queries,
                is_negative=True,
                proxy_query_range=(args.min_proxy_queries, args.max_proxy_queries)
            )
            negative_available_queries -= used_negative_queries
            # if len(negative_records) > last_len:
            #     last_len = len(negative_records)
            #     retries = 0
            # else:
            #     retries += 1
            #     if retries >= 5:
            #         break
    
    # Combine and shuffle records for even distribution
    all_records = positive_records + negative_records
    #random.shuffle(all_records)

    #if len(all_records) > total_limit:
    #    all_records = all_records[:total_limit]
    
    if len(all_records) > 0:
        post_process_visit_date(all_records)
        assign_frec_pct(all_records)
        assign_domain_frec_pct(all_records)
        # Rearrange columns to final order
        for record in all_records:
            record[4], record[5], record[6] = record[5], record[6], record[4]

        #columns = ['url', 'host', 'title', 'visit_date', 'category', 'intent', 'frecency_pct', 'domain_frecency_pct', 'is_negative']
        columns = ['url', 'host', 'title', 'visit_date', 'frecency_pct', 'domain_frecency_pct', 'is_negative']
        df = pd.DataFrame(columns=columns, data=all_records)
        df.to_csv(os.path.join(args.output_dir, fname[:-4] + "csv"), index=False)
        with open(os.path.join(args.output_dir, "queries_" + fname[:-4] + "json"), "w") as _o:
            json.dump({"positive": sorted(used_positive_queries), "negative": sorted(used_negative_queries)}, _o, indent=2)

        pos_count = sum(1 for r in all_records if not r[6])  # is_negative is now at index 8
        neg_count = sum(1 for r in all_records if r[6])
        actual_pct = (neg_count / len(all_records) * 100) if all_records else 0
        print(f"{fname}: {len(all_records)} records ({pos_count} positive, {neg_count} negative = {actual_pct:.1f}%)")


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