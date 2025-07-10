## Quick Start
Installation
```bash

```python
python fastapi_server/app_test_agent.py
```
## Setting LLM-API
```text
scripts/llm_load.py
```
## Customizing LangGraph Agents
step 1: Graph_dir
  ```text
  agent_main/agent.py
  agent_locate/agent.py
  agent_retrieve/agent.py
  ```
step 2: Modifying project code
  ```text
  project/app.py:
    TaskCollection: Adding funcs
    downstream/merge_all_results/flatten_and_tag: Adding branches
  ```
