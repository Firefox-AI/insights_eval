import os
import json
import time
from ddgs import DDGS
from ddgs.exceptions import TimeoutException, DDGSException


client = DDGS()

QUERY_DIR = "./data/negative_queries"
WEBSITE_DIR = "./data/negative_websites"

if not os.path.isdir(WEBSITE_DIR):
    os.makedirs(WEBSITE_DIR)


def get_ddgs_results(query, max_results=5):
    """Fetch DuckDuckGo search results for a query with retry logic.
    
    Args:
        query: Search query string.
        max_results: Maximum number of results to fetch (default 5).
        
    Returns:
        List of dicts with 'title' and 'url' keys.
    """
    results = []
    for i in range(1, 11):
        try:
            results = client.text(query, max_results=max_results)
            break
        except TimeoutException:
            elapse = 5 * i * i
            time.sleep(elapse)
        except DDGSException as err:
            results = []
            break

    if not results:
        print(f"Failed to retrieve result after 10 retries for: {query}")

    ret = [
        {
            "title": obj['title'],
            "url": obj['href']
        } for obj in results
    ]

    return ret


def get_websites(file_name):
    """Fetch websites for all queries in a persona file.
    
    Args:
        file_name: Name of the query JSON file.
        
    Returns:
        Dict mapping queries to their search results.
    """
    with open(os.path.join(QUERY_DIR, file_name)) as f:
        queries = json.load(f)

    ret = dict()
    for idx, query in enumerate(queries):
        websites = get_ddgs_results(query)
        ret[query] = websites

        if (idx + 1) % 10 == 0:
            print(f"Finished {idx+1} / {len(queries)} queries...")

    return ret


def main():
    """Main execution function."""
    query_files = sorted([
        fname for fname in os.listdir(QUERY_DIR) 
        if fname.endswith("json")
    ])


    for idx, fname in enumerate(query_files):
        dest_file_name = os.path.join(WEBSITE_DIR, fname)

        if os.path.exists(dest_file_name):
            print(f"[{idx+1}/{len(query_files)}] Skipping {fname} (already exists)")
            continue
            
        print(f"[{idx+1}/{len(query_files)}] Processing {fname}")
        results = get_websites(fname)

        with open(dest_file_name, "w") as f:
            json.dump(results, f, indent=2)

        print(f"Finished {idx+1}/{len(query_files)} files\n")

    print(f"\nAll done. Saved to {WEBSITE_DIR}/")


if __name__ == "__main__":
    main()
