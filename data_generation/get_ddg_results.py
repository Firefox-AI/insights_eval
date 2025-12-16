import os
import json
import time
from multiprocessing import Pool
from ddgs import DDGS
from ddgs.exceptions import TimeoutException, DDGSException


client = DDGS()

QUERY_DIR = "./queries"
WEBSITE_DIR = "./websites"

if not os.path.isdir(WEBSITE_DIR):
    os.makedirs(WEBSITE_DIR)


def get_ddgs_results(query, max_results=5):
    results = []
    for i in range(1, 11):
        try:
            results = client.text(query, max_results=max_results)
            break
        except TimeoutException:
            elapse = 5 * i * i
            print(f"Sleep for {elapse} seconds.")
            time.sleep(elapse)
        except DDGSException as err:
        #    if "No results found" in str(err):
            results = []
            break
        #    else:
        #        raise err
        #except Exception as err:
        #    raise err

    if not results:
        print("Failed to retrieve result after 10 retries.")

    ret = [
        {
            "title": obj['title'],
            "url": obj['href']
        } for obj in results
    ]

    return ret


def get_websites(file_name):
    with open(os.path.join(QUERY_DIR, file_name)) as f:
        queries = json.load(f)

    ret = dict()
    for idx, query in enumerate(queries):
        websites = get_ddgs_results(query)
        ret[query] = websites

        if (idx + 1) % 10:
            print(f"Finished {idx+1} / {len(queries)} queries...")

    return ret


def write_query_websites(results, query_files):
    if not os.path.isdir(WEBSITE_DIR):
        os.makedirs(WEBSITE_DIR)

    for fname, res in zip(query_files, results):
        with open(os.path.join(WEBSITE_DIR, fname), "w") as f:
            json.dump(res, f, indent=2)


def main():
    query_files = sorted([fname for fname in os.listdir(QUERY_DIR) if fname.endswith("json")])

    #with Pool(len(query_files)) as p:
    #    results = p.map(get_websites, query_files)

    #write_query_websites(results, query_files)
    # Won't work due to rate limiter

    for idx, fname in enumerate(query_files):
        dest_file_name = os.path.join(WEBSITE_DIR, fname)
        if os.path.exists(dest_file_name):
            print(f"Finished {idx+1} files.", flush=True)
            continue
        print(dest_file_name)
        results = get_websites(fname)

        with open(dest_file_name, "w") as f:
            json.dump(results, f, indent=2)

        print(f"Finished {idx+1} files.", flush=True)


if __name__ == "__main__":
    main()

