import os
import random
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tok.tokenize import tokenize  # noqa: E402

rng = random.Random(42)
words = ["search", "index", "Ünïcödé", "don't", "naïve", "café", "x", "tokenizer", "ﬁle", "２０２６"]
corpus = [" ".join(rng.choice(words) for _ in range(40)) for _ in range(20_000)]

start = time.perf_counter()
n = sum(len(tokenize(line)) for line in corpus)
print(f"tokenize: {n} tokens in {(time.perf_counter() - start) * 1000:.0f} ms")
