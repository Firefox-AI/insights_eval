import os
import re
import glob
import json
import yaml
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from openai import OpenAI
from pydantic import BaseModel
from argparse import ArgumentParser
from typing import Dict, List, Union
from concurrent.futures import ThreadPoolExecutor, as_completed

# From https://github.com/gregtatum/ml-driver/tree/main
from firefox_inference import FirefoxInference


# Turn off httpx logging from openai
logging.getLogger("httpx").setLevel(logging.ERROR)


# Config File Models
class DataConfig(BaseModel):
    records_path: str
    websites_path: str

class LiteLLMConfig(BaseModel):
    api_key: str
    endpoint: str
    fastly_request_key: str
    model: str

class OpenAIConfig(BaseModel):
    api_key: str
    model: str

class MemoriesGenerationConfig(BaseModel):
    max_threads: int
    n_passes: int

class MetricsComputationConfig(BaseModel):
    max_threads: int

class OutputConfig(BaseModel):
    metrics: str
    results: str

class MemoryEvaluatorConfig(BaseModel):
    data: DataConfig
    lite_llm: LiteLLMConfig
    firefox_repo_path: str
    openai: OpenAIConfig
    memories_generation: MemoriesGenerationConfig
    metrics_computation: MetricsComputationConfig
    output: OutputConfig

# Firefox Selenium driver JS script template
EVAL_JS_SCRIPT_HEADER = """
var callback = arguments[arguments.length - 1];

const { openAIEngine } = ChromeUtils.importESModule(
  "moz-src:///browser/components/aiwindow/models/Utils.sys.mjs"
);
const {
  sessionizeVisits,
  generateProfileInputs,
  aggregateSessions,
  topkAggregates,
} = ChromeUtils.importESModule("moz-src:///browser/components/aiwindow/models/InsightsHistorySource.sys.mjs");
const {
  HISTORY,
  CONVERSATION
} = ChromeUtils.importESModule("moz-src:///browser/components/aiwindow/models/InsightsConstants.sys.mjs");
const { generateInsights } = ChromeUtils.importESModule(
  "moz-src:///browser/components/aiwindow/models/Insights.sys.mjs"
);

async function runCallback() {

  // Prep synthetic history
  const rows = """

EVAL_JS_SCRIPT_FOOTER = """
  const sessionized = sessionizeVisits(rows);
  const profilePreparedInputs = generateProfileInputs(sessionized);
  const [domainAgg, titleAgg, searchAgg] = aggregateSessions(
      profilePreparedInputs
  );
  const [domainItems, titleItems, searchItems] = await topkAggregates(
    domainAgg,
    titleAgg,
    searchAgg,
    {
      k_domains: 100,
      k_titles: 60,
      k_searches: 10,
      now: undefined,
    }
  );
  const sources = {history: [domainItems, titleItems, searchItems]};

  // Generate memories
  const engine = await openAIEngine.build("smart-openai", "ai");

  return await generateInsights(engine, sources, []);
}
runCallback().then(result => callback(result));
"""

# Search engine regex
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
SEARCH_ENGINE_REGEX = re.compile(
    rf"(?:^|\.){'|'.join(SEARCH_ENGINE_DOMAINS)}\.", re.IGNORECASE
)

# Markdown JSON extraction regex
JSON_REGEX = re.compile(r"(?:```json)?([\[\{].*[\}\]])(?:```)?", re.DOTALL)


class MemoryEvaluator:
    """
    Generates and evaluates memories based on mock browsing history
    """

    def __init__(
        self,
        config: MemoryEvaluatorConfig
    ):

        self.config = config
        self.aiwindow_prefs = MemoryEvaluator.set_aiwindow_prefs(config.lite_llm)
        self.firefox_bin = MemoryEvaluator.get_firefox_bin_path(config.firefox_repo_path)
        self.openai_client = OpenAI(api_key=config.openai.api_key)

    @staticmethod
    def set_aiwindow_prefs(lite_llm_config: LiteLLMConfig) -> Dict[str, str]:
        """
        Sets AI Window preferences for the Firefox Selenium driver
        """
        return {
            "browser.aiwindow.apiKey": lite_llm_config.api_key,
            "browser.aiwindow.endpoint": lite_llm_config.endpoint,
            "browser.aiwindow.model": lite_llm_config.model,
            "browser.aiwindow.extraHeaders": '{"X-FASTLY-REQUEST": '+f'"{lite_llm_config.fastly_request_key}"'+'}'
        }

    @staticmethod
    def get_firefox_bin_path(firefox_repo_path: str) -> Path:
        """
        Finds the latest compiled Firefox binary
        """
        bin_dir_opts = glob.glob(f"{firefox_repo_path}/obj-*/dist/Nightly.app/Contents/MacOS/firefox")
        return Path(max(bin_dir_opts, key=os.path.getctime))

    @staticmethod
    def is_search_engine_url(url: str) -> str:
        """
        Determines if a URL is from a search engine
        """
        if SEARCH_ENGINE_REGEX.findall(url):
            return "search"
        return "history"

    def generate_memories(self, profile_files: List[str], batch_id: int) -> Dict[str, List]:
        """
        Generates memories for a batch of profile files
        """
        log_header = f"[Thread {batch_id}]"
        all_results = {}
        total_profiles = len(profile_files)
        for profile_id, profile_file in enumerate(profile_files):
            profile_name = profile_file.split("/")[-1].replace(".csv", "")
            profile_log_header = log_header + f"[{profile_id+1}/{total_profiles}]"
            print(f"{profile_log_header} Generating memories for profile \"{profile_name}\"")

            profile_data = pd.read_csv(profile_file)
            profile_data = profile_data.drop(["category", "intent"], axis=1)
            profile_data.columns = ["url", "domain", "title", "visitDateMicros", "frequencyPct", "domainFrequencyPct"]
            profile_data["source"] = profile_data["url"].map(lambda url: MemoryEvaluator.is_search_engine_url(url))

            # Render eval JS script with data injected
            eval_js_script = EVAL_JS_SCRIPT_HEADER + profile_data.to_json(orient="records") + EVAL_JS_SCRIPT_FOOTER

            # Set up the Selenium Firefox driver
            firefox = FirefoxInference(
                firefox_bin=self.firefox_bin,
                headless=True,
                ml_prefs=self.aiwindow_prefs
            )
            firefox.driver.set_context(firefox.driver.CONTEXT_CHROME)
            firefox.driver.set_script_timeout(180)

            results = []
            for _ in range(self.config.memories_generation.n_passes):
                memories = firefox.driver.execute_async_script(eval_js_script)
                results.append(memories)

            firefox.quit()
            all_results[profile_name] = results
            print(f"{profile_log_header} Completed memories for \"{profile_name}\"")
        return all_results

    def batch_generate_memories(self) -> Dict:
        """
        Orchestrates multiprocessing for running memory generation from profile file batches
        """

        mem_gen_conf = self.config.memories_generation

        profile_files = glob.glob(f"{self.config.data.records_path}/*.csv")

        profile_file_batches = np.array_split(np.array(profile_files), min(len(profile_files), mem_gen_conf.max_threads))

        tasks = []
        generated_memories = {}
        with ThreadPoolExecutor(max_workers=mem_gen_conf.max_threads) as executor:
            for batch_id, profile_file_batch in enumerate(profile_file_batches):
                tasks.append(
                    executor.submit(
                        self.generate_memories,
                        profile_file_batch,
                        batch_id
                    )
                )
            for task in as_completed(tasks):
                generated_memories |= task.result()

        return generated_memories

    @staticmethod
    def extract_and_parse_json_response(response: str) -> Dict:
        """
        Finds and extract JSON markdown content from an LLM response
        """
        return json.loads(JSON_REGEX.findall(response)[0])

    def compare_memory_to_queries(self, memory: str, used_queries: List[str]) -> List[str]:
        """
        Prompts an LLM to compare a single generated memory to existing search queries to find related sets
        """

        prompt = f"""
Determine if any of the below Search Queries are related to the Statement. You may find multiple related queries, but be strict in your assessment.
For a query to be related to the Statement, it must:
1. Be highly semantically similar to the Statement.
2. Reference identical or similar entities, topics, or concepts as the Statement.
3. Can be used as evidence for the Statement.

Statement: "{memory}"

Search Queries:
- {"\n- ".join(['"' + query + '"' for query in used_queries])}

BE STRICT IN YOUR ASSESEMENT AND ADHERE TO THE ABOVE CRITERIA. Prefer to return an empty list than loosely or partially related queries.

Give your answer as a JSON list in the following format:
```json
[
    "Related Query 1",
    "Related Query 2",
    ...
]
```
"""
        while True:
            try:
                resp = self.openai_client.chat.completions.create(
                    model=self.config.openai.model,
                    messages=[
                        {"role": "system", "content": "You are an expert at finding relationships between statements and search queries."},
                        {"role": "user", "content": prompt},
                    ],
                )
                comparison_json_out = [query for query in MemoryEvaluator.extract_and_parse_json_response(resp.choices[0].message.content) if query in used_queries]
                break
            except Exception as e:
                print(f"Failed to extract insight/query comparison data: {e}")
                continue
        return comparison_json_out

    def find_duplicates(self, memories: List[str]) -> List[List[str]]:
        """
        Prompts an LLM to identify close or identical semantic duplicates in a set of memories
        """

        prompt = """
Examine the list of statements below and determine if there are any groups of statements that express the exact same semantic meaning with different wording.
If you identify such groups, provide them as lists below. Each statement must only belong to a single list, so if you want to add a statement to multiple lists, combine the lists.

Statements:""" + f"""
- {"\n- ".join(['"' + memory + '"' for memory in memories])}""" + """

Along with your answer, provide your justification and reasoning.
Give your answer as a JSON object in the following format:
```json
{
    "justification": "your justification here",
    "similar_statement_groups": [
        ["Duplicate Statement 1.1", "Duplicate Statement 1.2", "Duplicate Statement 1.3"],
        ["Duplicate Statement 2.1", "Duplicate Statement 2.2"],
        ...
    ]
}
```
If you do not identify any groups of such statements, simply return an empty list with your justification.
"""
        while True:
            try:
                resp = self.openai_client.chat.completions.create(
                    model=self.config.openai.model,
                    messages=[
                        {"role": "system", "content": "You are an expert at finding groups of similar statements."},
                        {"role": "user", "content": prompt}
                    ]
                )
                dup_json_out = MemoryEvaluator.extract_and_parse_json_response(resp.choices[0].message.content)
                break
            except Exception as e:
                print(f"Failed to extract duplicates list: {e}")
                continue

        return dup_json_out

    def compute_metrics(self, results_df: pd.DataFrame, used_queries: List[str]):
        """
        Computes evaluation metrics for a profile's generated memories
        """

        run_ids = set(results_df["run_idx"].tolist())
        results = []

        for run_id in sorted(run_ids):
            run_df = results_df[results_df["run_idx"] == run_id]
            total_rows = len(run_df)

            # Coverage -> each memory has at least 1 query
            memories_with_at_least_one_query = len(run_df[run_df["count_related_queries"] > 0])

            # Extra -> memories without a query
            memories_without_a_query = len(run_df[run_df["count_related_queries"] == 0])

            # Missing -> queries without an memory
            query_coverage_counts = {query: set() for query in used_queries}
            for _, row in run_df.iterrows():
                for related_query in row["related_queries"]:
                    query_coverage_counts[related_query].add(row["insight_summary"])
            queries_without_a_memory = [query for query, related_memory_set in query_coverage_counts.items() if len(related_memory_set) == 0]
            queries_without_a_memory_count = len(queries_without_a_memory)

            # Duplicates -> memories mapped to the same query
            generated_memories = run_df["insight_summary"].tolist()
            duplicates_out = self.find_duplicates(generated_memories)
            duplicate_memories = set()
            for similar_statement_group in duplicates_out["similar_statement_groups"]:
                duplicate_memories |= set([similar_memory for similar_memory in similar_statement_group if similar_memory in generated_memories])

            results.append({
                "run_id": run_id,
                "total_memories_generated": total_rows,
                "total_queries": len(used_queries),
                "coverage_count": memories_with_at_least_one_query,
                "coverage_perc": memories_with_at_least_one_query / total_rows,
                "extra_count": memories_without_a_query,
                "extra_perc": memories_without_a_query / total_rows,
                "missing_count": queries_without_a_memory_count,
                "missing_perc": queries_without_a_memory_count / len(used_queries),
                "queries_without_a_memory": queries_without_a_memory,
                "duplicate_count": len(duplicate_memories),
                "duplicate_perc": len(duplicate_memories) / total_rows
            })

        final_results = pd.DataFrame(results)

        return final_results

    def aggregate_metrics(self, personas: List[str], generated_memories: Dict[str, List[List[str]]], batch_id: str) -> Union[List, List]:
        """
        Aggregates eval metrics for a batch of personas
        """

        log_header = f"[Thread {batch_id}]"
        all_metrics = []
        all_results = []
        total_personas = len(personas)
        for persona_id, persona in enumerate(personas):
            persona_log_header = log_header + f"[{persona_id+1}/{total_personas}]"
            print(f"{persona_log_header} Aggregating metrics for \"{persona}\"")
            persona_source_data = pd.read_csv(f"{self.config.data.records_path}/{persona}.csv")
            with open(f"{self.config.data.websites_path}/{persona}.json", "r") as _j:
                persona_metadata = json.load(_j)

            persona_used_queries = [
                query for query, pages in persona_metadata.items() if len(set([page["url"] for page in pages]).intersection(set(persona_source_data["url"].tolist()))) > 0
            ]

            persona_results_list = []
            for run_idx, batch in enumerate(generated_memories[persona]):
                for memory in batch:
                    persona_results_list.append({
                        "run_idx": run_idx,
                        **memory
                    })
            persona_results_df = pd.DataFrame(persona_results_list)
            persona_results_df["related_queries"] = persona_results_df["insight_summary"].map(
                lambda memory_summary: self.compare_memory_to_queries(memory_summary, persona_used_queries)
            )
            persona_results_df["count_related_queries"] = persona_results_df["related_queries"].map(lambda related_queries: len(related_queries))
            persona_metrics_df = self.compute_metrics(persona_results_df, persona_used_queries)

            persona_metrics_df.insert(0, "persona_id", [persona] * len(persona_metrics_df))
            persona_results_df.insert(0, "persona_id", [persona] * len(persona_results_df))

            print(f"{persona_log_header} Completed aggregating metrics for \"{persona}\"")
            all_metrics.append(persona_metrics_df)
            all_results.append(persona_results_df)
        return all_metrics, all_results

    def batch_aggregate_metrics(self, generated_memories: Dict[str, List[List[str]]]) -> pd.DataFrame:
        """
        Orchestrates multiprocessing for eval metrics aggregation
        """

        metrics_comp_conf = self.config.metrics_computation
        all_personas = list(generated_memories.keys())
        persona_batches = np.array_split(np.array(all_personas), min(len(all_personas), metrics_comp_conf.max_threads))

        tasks = []
        computed_metrics = []
        all_results = []
        with ThreadPoolExecutor(max_workers=metrics_comp_conf.max_threads) as executor:
            for batch_id, persona_batch in enumerate(persona_batches):
                tasks.append(
                    executor.submit(
                        self.aggregate_metrics,
                        persona_batch,
                        generated_memories,
                        batch_id
                    )
                )
            for task in as_completed(tasks):
                task_metrics, task_results = task.result()
                computed_metrics += task_metrics
                all_results += task_results
        return pd.concat(computed_metrics), pd.concat(all_results)

    def run(self) -> pd.DataFrame:
        """
        Main runner function
        """

        generated_memories = self.batch_generate_memories()
        return self.batch_aggregate_metrics(generated_memories)

def get_args():
    parser = ArgumentParser()
    parser.add_argument("-c", "--config", required=True, help="Memories evaluation config file")
    return parser.parse_args()

def main():
    args = get_args()
    with open(args.config, "r") as _y:
        config = MemoryEvaluatorConfig(**yaml.safe_load(_y))
    print(config)
    memories_evalutor = MemoryEvaluator(config)
    metrics_df, results_df = memories_evalutor.run()
    metrics_df.to_csv(config.output.metrics)
    results_df.to_csv(config.output.results)


if __name__ == "__main__":
    main()
