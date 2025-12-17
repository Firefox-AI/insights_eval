## This repository is for the work of AI-mode insight model evaluation


### Profile Generation
There are multiple steps to generate the profiles and persona for this evaluation work, all the scripts are in data_generation directory.
Please execute the code under data_generation directory.

1. The base persona file is created by chatGPT, but it can be any json file like it as long as it includes "persona_name" and "description" for later use.
2. Run `python build_persona.py` or `python build_complex_persona.py` to create realistic persona.
3. Run `python create_queries_from_persona.py` to create possible queries from each persona.
4. Run `python get_ddg_results.py` to retrieve top N search results for each query.
5. Run `python label_queries_and_websites.py` to label category and intent of each query / page.
6. Run `python synthesize_intermediate_profiles.py` to synthesize user profile intermediate result as input of evaluation pipeline.
