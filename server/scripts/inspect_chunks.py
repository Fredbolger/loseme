"""
Inspect Qdrant collection stats and chunk size distribution.

Usage (from project root):
    docker compose exec server python -m scripts.inspect_chunks

Output:
    - Stats printed to stdout
    - chunk_stats.png written to /mnt/userdata (i.e. LOSEME_HOST_ROOT on the host)
"""

import statistics
import collections
import os

import matplotlib
matplotlib.use("Agg")  # no display needed
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

from qdrant_client import QdrantClient

QDRANT_URL  = os.getenv("QDRANT_URL", "http://qdrant:6333")
COLLECTION  = "chunks"
OUTPUT_PATH = "/mnt/userdata/chunk_stats.png"


def main():
    client = QdrantClient(url=QDRANT_URL)

    info = client.get_collection(COLLECTION)
    print(f"\n=== Collection: {COLLECTION} ===")
    print(f"  Total points : {info.points_count}")
    print(f"  Status       : {info.status}")

    # --- Scroll all payloads ---
    char_lens     = []
    chunks_per_doc = collections.Counter()
    source_types  = collections.Counter()
    source_paths  = collections.Counter()

    offset        = None
    total_scanned = 0

    while True:
        result, next_offset = client.scroll(
            collection_name=COLLECTION,
            limit=500,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for point in result:
            meta = point.payload.get("metadata", {})
            char_len = meta.get("char_len")
            if char_len is not None:
                char_lens.append(char_len)
            path = point.payload.get("source_path", "unknown")
            source_types[point.payload.get("source_type", "unknown")] += 1
            source_paths[path] += 1
            chunks_per_doc[path] += 1

        total_scanned += len(result)
        print(f"  Scanned {total_scanned} points...", end="\r")

        if next_offset is None:
            break
        offset = next_offset

    print(f"\n")

    # --- stdout stats ---
    _print_char_len_stats(char_lens)

    print(f"\n=== Source types ===")
    for stype, count in source_types.most_common():
        print(f"  {stype:20} {count}")

    print(f"\n=== Top 20 source paths by chunk count ===")
    for path, count in source_paths.most_common(20):
        print(f"  {count:5}  {path}")

    # --- Plot ---
    _plot(char_lens, chunks_per_doc)


def _print_char_len_stats(char_lens):
    print(f"=== Chunk text size (char_len) ===")
    if not char_lens:
        print("  No char_len found in metadata.")
        return

    char_lens_sorted = sorted(char_lens)
    n = len(char_lens_sorted)
    print(f"  Count  : {n}")
    print(f"  Min    : {char_lens_sorted[0]}")
    print(f"  p25    : {char_lens_sorted[n // 4]}")
    print(f"  Median : {char_lens_sorted[n // 2]}")
    print(f"  p75    : {char_lens_sorted[3 * n // 4]}")
    print(f"  p95    : {char_lens_sorted[int(n * 0.95)]}")
    print(f"  Max    : {char_lens_sorted[-1]}")
    print(f"  Mean   : {statistics.mean(char_lens):.1f}")
    print(f"  StdDev : {statistics.stdev(char_lens):.1f}")


def _plot(char_lens: list, chunks_per_doc: collections.Counter):
    if not char_lens:
        print("  No data to plot.")
        return

    doc_counts = list(chunks_per_doc.values())

    fig = plt.figure(figsize=(14, 10))
    fig.suptitle("Chunk Storage Analysis", fontsize=15, fontweight="bold")
    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.4, wspace=0.35)

    # 1 — Chunk char_len histogram (log y)
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.hist(char_lens, bins=60, color="#4C8BF5", edgecolor="white", linewidth=0.3)
    ax1.set_yscale("log")
    ax1.set_xlabel("Chunk size (chars)")
    ax1.set_ylabel("Count (log scale)")
    ax1.set_title("Chunk size distribution")
    _add_percentile_lines(ax1, char_lens)

    # 2 — Chunk char_len CDF
    ax2 = fig.add_subplot(gs[0, 1])
    sorted_lens = sorted(char_lens)
    n = len(sorted_lens)
    ax2.plot(sorted_lens, [i / n for i in range(n)], color="#4C8BF5", linewidth=1.2)
    ax2.set_xlabel("Chunk size (chars)")
    ax2.set_ylabel("Cumulative fraction")
    ax2.set_title("Chunk size CDF")
    ax2.grid(True, alpha=0.3)
    _add_percentile_lines(ax2, char_lens)

    # 3 — Chunks per document histogram (log y)
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.hist(doc_counts, bins=50, color="#F5A623", edgecolor="white", linewidth=0.3)
    ax3.set_yscale("log")
    ax3.set_xlabel("Chunks per document")
    ax3.set_ylabel("Number of documents (log scale)")
    ax3.set_title("Chunks per document distribution")
    _add_percentile_lines(ax3, doc_counts)

    # 4 — Top 20 worst offenders (horizontal bar)
    ax4 = fig.add_subplot(gs[1, 1])
    top20 = chunks_per_doc.most_common(20)
    labels = [os.path.basename(p) for p, _ in reversed(top20)]
    values = [c for _, c in reversed(top20)]
    bars = ax4.barh(labels, values, color="#E05C5C", edgecolor="white", linewidth=0.3)
    ax4.set_xlabel("Chunk count")
    ax4.set_title("Top 20 documents by chunk count")
    ax4.tick_params(axis="y", labelsize=6)
    # annotate values
    for bar, val in zip(bars, values):
        ax4.text(val + 1, bar.get_y() + bar.get_height() / 2,
                 str(val), va="center", fontsize=6)

    fig.savefig(OUTPUT_PATH, dpi=150, bbox_inches="tight")
    print(f"\n  Plot saved to {OUTPUT_PATH}")


def _add_percentile_lines(ax, data):
    s = sorted(data)
    n = len(s)
    for pct, label, color in [
        (0.50, "p50", "#888888"),
        (0.95, "p95", "#E05C5C"),
    ]:
        val = s[int(n * pct)]
        ax.axvline(val, color=color, linestyle="--", linewidth=1, alpha=0.8)
        ax.text(val, ax.get_ylim()[1] * 0.9, f" {label}={val}",
                color=color, fontsize=7, va="top")


if __name__ == "__main__":
    main()
