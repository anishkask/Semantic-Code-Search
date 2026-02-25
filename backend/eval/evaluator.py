"""
Evaluation framework for semantic code search.

Produces recall@k metrics against a manually verified eval set.

Concepts:
- Recall@k: For a query, if any correct answer appears in the top k results, it
  counts as a hit. Recall@k across N queries = hits / N. Binary per query.
- Manually verified answers: We need ground truth (acceptable_ids) because we
  cannot assume the top result is correct. Semantic search can rank plausible-
  but-wrong chunks first; only human verification gives reliable metrics.
- Recall@1 vs @3 vs @5: Recall@1 = strict (top result must be correct). Recall@3
  and @5 show whether correct answers appear when we relax the cutoff. A system
  with high @5 but low @1 needs better ranking; similar @1/@3/@5 suggests
  correct answers are either at the top or missing entirely.
"""

import json
from pathlib import Path
from typing import List, Dict, Any

import sys
_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from retrieval.retriever import search


def run_eval(
    eval_set_path: Path,
    collection_name: str,
    model: str = "local",
    k_values: List[int] = None,
) -> Dict[str, Any]:
    """
    Run evaluation against the eval set.

    For each query, runs search() and checks whether any acceptable_id appears
    in the top k results for each k value. Returns recall@k and per-query breakdown.

    Args:
        eval_set_path: Path to eval_set.json
        collection_name: ChromaDB collection name
        model: "local" or "openai"
        k_values: List of k values for recall@k (default [1, 3, 5])

    Returns:
        Dict with recall@1, recall@3, recall@5, and per_query breakdown
    """
    if k_values is None:
        k_values = [1, 3, 5]

    with open(eval_set_path, "r", encoding="utf-8") as f:
        eval_set = json.load(f)

    max_k = max(k_values)
    n_queries = len(eval_set)

    # Per-query results: query -> { k -> hit (bool) }
    per_query: Dict[str, Dict[int, bool]] = {}
    recall: Dict[int, float] = {k: 0.0 for k in k_values}

    for item in eval_set:
        query = item["query"]
        acceptable_ids = set(item["acceptable_ids"])
        results = search(
            query,
            collection_name=collection_name,
            model=model,
            n_results=max_k,
        )

        result_ids = [r.get("id", "") for r in results[:max_k]]

        per_query[query] = {}
        for k in k_values:
            top_k_ids = set(result_ids[:k])
            hit = bool(acceptable_ids & top_k_ids)
            per_query[query][k] = hit
            if hit:
                recall[k] += 1

    for k in k_values:
        recall[k] = recall[k] / n_queries if n_queries > 0 else 0.0

    return {
        "n_queries": n_queries,
        "recall": recall,
        "per_query": per_query,
        "k_values": k_values,
    }


def print_eval_report(results: Dict[str, Any]) -> None:
    """
    Print a clean table of recall@k and list failed queries.
    """
    n = results["n_queries"]
    recall = results["recall"]
    per_query = results["per_query"]
    k_values = results["k_values"]

    print("=" * 60)
    print("EVALUATION REPORT")
    print("=" * 60)
    print(f"\nQueries: {n}")
    print("\nRecall@k:")
    print("-" * 60)
    for k in sorted(k_values):
        r = recall[k]
        pct = r * 100
        print(f"  Recall@{k}: {r:.2%} ({int(r * n)}/{n})")
    print("-" * 60)

    # Failed queries by k
    for k in sorted(k_values):
        failed = [q for q, hits in per_query.items() if not hits[k]]
        if failed:
            print(f"\nFailed at Recall@{k} ({len(failed)} queries):")
            for q in failed:
                print(f"  - \"{q}\"")
        else:
            print(f"\nFailed at Recall@{k}: none")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    eval_path = Path(__file__).resolve().parent / "eval_set.json"
    print(f"Running evaluation on {eval_path}")
    print(f"Collection: flask_local, model: local\n")
    results = run_eval(
        eval_set_path=eval_path,
        collection_name="flask_local",
        model="local",
        k_values=[1, 3, 5],
    )
    print_eval_report(results)
