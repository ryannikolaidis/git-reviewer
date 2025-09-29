#!/usr/bin/env python3
"""Example of using git-reviewer Python API to get raw nllm results."""

from git_reviewer.api import review_repository

# Review the repository - returns raw nllm.NllmResults directly
nllm_results = review_repository(
    repo_path="/Users/ryannikolaidis/Development/concierge",
    models=["gpt-4.1"],  # Or None to use all configured models
    output_dir="/tmp/my-review"
)

# You get the unaltered nllm.NllmResults object directly
print("=== Raw nllm.NllmResults ===")
print(f"Total results: {len(nllm_results.results)}")
print(f"Manifest: {nllm_results.manifest}")
print()

# Access individual result objects
for i, nllm_result in enumerate(nllm_results.results):
    print(f"Result {i+1}: {nllm_result.model}")
    print(f"  Status: {nllm_result.status}")
    print(f"  Duration: {nllm_result.duration_ms}ms")
    print(f"  Exit code: {nllm_result.exit_code}")
    print(f"  Command: {' '.join(nllm_result.command)}")

    if hasattr(nllm_result, 'json') and nllm_result.json is not None:
        print(f"  Has parsed JSON: Yes")
        print(f"  JSON keys: {list(nllm_result.json.keys()) if isinstance(nllm_result.json, dict) else 'Not a dict'}")
    else:
        print(f"  Has parsed JSON: No")

    print(f"  Text length: {len(nllm_result.text) if nllm_result.text else 0}")
    if nllm_result.stderr_tail:
        print(f"  Error: {nllm_result.stderr_tail}")
    print()

# Simple success/failure summary
successes = [r for r in nllm_results.results if r.status == "ok"]
failures = [r for r in nllm_results.results if r.status != "ok"]

print(f"=== Summary ===")
print(f"Successful models: {[r.model for r in successes]}")
print(f"Failed models: {[r.model for r in failures]}")
print(f"Success rate: {len(successes)}/{len(nllm_results.results)}")