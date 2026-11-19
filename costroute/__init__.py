"""Cost-aware LLM routing: send each request to the cheapest model likely to answer it well.

The learned router uses measured local runs. The hosted portfolio records published token rates
and leaves unpublished cloud rates marked [verify]."""

__version__ = "0.1.0"
