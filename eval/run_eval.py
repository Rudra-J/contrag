"""
Run retrieval (Hit Rate@k, MRR, Mean Rank) and groundedness evaluation.
Requires eval/dataset.json — run generate_dataset.py first.

Usage:
    python eval/run_eval.py                    # both passes
    python eval/run_eval.py --retrieval-only   # skip groundedness
    python eval/run_eval.py --groundedness-only
    python eval/run_eval.py --k 3              # change retrieval depth (default 5)
    python eval/run_eval.py --sample 50        # evaluate on a random sample

Results are printed to stdout and saved to eval/results/<timestamp>.json.
"""

import sys, os, json, re, argparse, random
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

DATASET_PATH = "eval/dataset.json"
RESULTS_DIR  = "eval/results"
MODEL        = "llama3.2"

# ── RAG prompt (mirrors chain.py) ────────────────────────────────────────────

_RAG_PROMPT = """\
You are a legal contract analyst.
Answer the question using ONLY the contract clauses below.
Follow these rules strictly:

1. Quote or paraphrase ONLY what is explicitly written. Do not infer relationships,
   draw conclusions, or fill in gaps — even if they seem obvious.
2. If a field appears blank or contains a placeholder (e.g. underscores, empty lines),
   state that it is not filled in. Do not guess the value.
3. If clauses from multiple contracts are provided, keep each contract's information
   separate. Never mix facts from different source files.
4. Cite every claim with its source: [Clause from: filename, Section X].
5. If the answer is not found in the clauses, respond with exactly:
   "This is not addressed in the uploaded contracts."

CONTRACT CLAUSES:
{context}

QUESTION: {question}

ANSWER:"""

# ── Groundedness judge prompt ─────────────────────────────────────────────────

_JUDGE_PROMPT = """\
You are evaluating whether a RAG system's answer is grounded in its retrieved context.

RETRIEVED CONTEXT:
{context}

QUESTION:
{question}

ANSWER:
{answer}

Task: Does the answer introduce any NEW FACTUAL CLAIM that is absent from the context?
Rules:
- Accurate paraphrasing or summarising of context counts as grounded = true.
- Citing a source file or section label that appears in the context counts as grounded = true.
- Only mark grounded = false if the answer states a specific fact (a number, name, date,
  legal provision, or obligation) that cannot be found anywhere in the context above.
- Do NOT penalise the answer for omitting information; only penalise for adding false facts.

Respond ONLY with valid JSON — no markdown, no text outside the JSON:
{{"grounded": true, "reason": "one sentence explanation"}}
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_dataset(path: str, sample: int | None) -> list:
    if not os.path.exists(path):
        print(f"ERROR: {path} not found. Run generate_dataset.py first.")
        sys.exit(1)
    with open(path) as f:
        data = json.load(f)
    if sample and sample < len(data):
        data = random.sample(data, sample)
        print(f"Sampled {sample} questions from {path}.")
    return data


def _normalize(text: str) -> str:
    return " ".join(text.strip().split())


def _extract_json(text: str) -> dict:
    text = re.sub(r"```json|```", "", text).strip()
    return json.loads(text)


def _format_context(docs) -> str:
    return "\n\n---\n\n".join(
        f"[Clause from: {d.metadata.get('source', 'unknown')}]\n{d.page_content}"
        for d in docs
    )


# ── Retrieval eval ────────────────────────────────────────────────────────────

def run_retrieval_eval(dataset: list, k: int) -> dict:
    from retriever import retrieve_with_metrics

    print(f"\n-- Retrieval Eval  k={k}  n={len(dataset)} --")

    reciprocal_ranks   = []
    ranks_when_found   = []
    hits               = 0

    for i, item in enumerate(dataset):
        source_chunk = _normalize(item["source_chunk"])
        result       = retrieve_with_metrics(item["question"], k=k)
        retrieved    = [_normalize(d.page_content) for d in result["docs"]]

        rank = next(
            (j + 1 for j, chunk in enumerate(retrieved) if chunk == source_chunk),
            None,
        )

        if rank is not None:
            hits += 1
            reciprocal_ranks.append(1.0 / rank)
            ranks_when_found.append(rank)
        else:
            reciprocal_ranks.append(0.0)

        if (i + 1) % 20 == 0 or (i + 1) == len(dataset):
            print(f"  {i+1}/{len(dataset)} evaluated  "
                  f"(running Hit Rate: {hits/(i+1):.2f})")

    n         = len(dataset)
    hit_rate  = hits / n
    mrr       = sum(reciprocal_ranks) / n
    mean_rank = sum(ranks_when_found) / len(ranks_when_found) if ranks_when_found else None

    print(f"\n  Hit Rate@{k}  : {hit_rate:.3f}  ({hits}/{n})")
    print(f"  MRR          : {mrr:.3f}")
    if mean_rank:
        print(f"  Mean Rank    : {mean_rank:.1f}  (when found)")

    return {
        "k":         k,
        "n":         n,
        "hits":      hits,
        "hit_rate":  round(hit_rate, 4),
        "mrr":       round(mrr, 4),
        "mean_rank": round(mean_rank, 2) if mean_rank else None,
    }


# ── Groundedness eval ─────────────────────────────────────────────────────────

def run_groundedness_eval(dataset: list) -> dict:
    from retriever import retrieve_with_metrics
    from langchain_ollama import ChatOllama

    llm = ChatOllama(model=MODEL, temperature=0)

    print(f"\n-- Groundedness Eval  n={len(dataset)} --")

    grounded_count = 0
    skipped        = 0
    ungrounded     = []

    for i, item in enumerate(dataset):
        question = item["question"]

        try:
            # Single retrieval pass — used for both answer generation and judging
            result  = retrieve_with_metrics(question)
            context = _format_context(result["docs"])

            # Generate answer with the same RAG prompt as the live system
            answer_resp = llm.invoke(_RAG_PROMPT.format(context=context, question=question))
            answer      = answer_resp.content.strip()

            # Judge groundedness
            judge_resp = llm.invoke(
                _JUDGE_PROMPT.format(context=context, question=question, answer=answer)
            )
            judgment = _extract_json(judge_resp.content)

            if judgment.get("grounded", False):
                grounded_count += 1
            else:
                ungrounded.append({
                    "question": question,
                    "answer":   answer[:300],
                    "reason":   judgment.get("reason", ""),
                })

        except Exception as e:
            skipped += 1
            continue

        if (i + 1) % 20 == 0 or (i + 1) == len(dataset):
            evaluated = i + 1 - skipped
            rate      = grounded_count / evaluated if evaluated else 0
            print(f"  {i+1}/{len(dataset)} judged  "
                  f"(running Groundedness: {rate:.2f}  skipped: {skipped})")

    evaluated         = len(dataset) - skipped
    groundedness_rate = grounded_count / evaluated if evaluated else 0

    print(f"\n  Groundedness : {groundedness_rate:.3f}  "
          f"({grounded_count}/{evaluated}  skipped: {skipped})")

    if ungrounded:
        print(f"\n  Sample ungrounded answers ({min(3, len(ungrounded))}):")
        for ex in ungrounded[:3]:
            print(f"    Q: {ex['question'][:90]}")
            print(f"    Reason: {ex['reason'][:120]}")
            print()

    return {
        "n":                 len(dataset),
        "evaluated":         evaluated,
        "skipped":           skipped,
        "grounded":          grounded_count,
        "groundedness_rate": round(groundedness_rate, 4),
        "ungrounded_sample": ungrounded[:10],
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Contrag RAG evaluation pipeline")
    parser.add_argument("--retrieval-only",    action="store_true")
    parser.add_argument("--groundedness-only", action="store_true")
    parser.add_argument("--k",      type=int, default=5,    help="Retrieval depth (default 5)")
    parser.add_argument("--sample", type=int, default=None, help="Evaluate on N random questions")
    args = parser.parse_args()

    dataset = _load_dataset(DATASET_PATH, args.sample)
    print(f"Dataset: {len(dataset)} questions from {DATASET_PATH}")

    results = {
        "timestamp":    datetime.now().isoformat(),
        "dataset_size": len(dataset),
        "model":        MODEL,
    }

    if not args.groundedness_only:
        results["retrieval"] = run_retrieval_eval(dataset, k=args.k)

    if not args.retrieval_only:
        results["groundedness"] = run_groundedness_eval(dataset)

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n==============================")
    print(" Contrag Eval Summary")
    print("==============================")
    if "retrieval" in results:
        r = results["retrieval"]
        print(f" Hit Rate@{r['k']}  : {r['hit_rate']:.3f}")
        print(f" MRR         : {r['mrr']:.3f}")
        if r["mean_rank"]:
            print(f" Mean Rank   : {r['mean_rank']:.1f}")
    if "groundedness" in results:
        g = results["groundedness"]
        print(f" Groundedness: {g['groundedness_rate']:.3f}")
    print("==============================")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts       = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    out_path = os.path.join(RESULTS_DIR, f"{ts}.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nFull results -> {out_path}")


if __name__ == "__main__":
    main()
