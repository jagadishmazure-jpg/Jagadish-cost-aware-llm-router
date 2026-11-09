"""Learned router: one calibrated "will this model get it right?" classifier per model.

The router only sees the prompt text, never the task family or the answer. For each model it predicts
P(correct | prompt). The policy picks the cheapest allowed model whose predicted quality clears a
threshold; if none does, it picks the largest allowed model.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

_NUM = re.compile(r"\d+")


def shape_features(texts) -> np.ndarray:
    rows = []
    for t in texts:
        nums = _NUM.findall(t)
        rows.append([len(t.split()), len(nums), sum(len(n) for n in nums), t.count("?"),
                     float("json" in t.lower()), float(bool(re.search(r"\d{4}-\d{2}-\d{2}", t))),
                     float("classify" in t.lower())])
    return np.array(rows, dtype=float)


def build_features() -> FeatureUnion:
    return FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=3, sublinear_tf=True,
                                 max_features=20000)),
        ("shape", Pipeline([("f", FunctionTransformer(shape_features)), ("s", StandardScaler())])),
    ])


@dataclass
class QualityPredictor:
    models: list[str]
    C: float = 3.0
    _feats: FeatureUnion | None = None
    _clf: dict = field(default_factory=dict)

    def fit(self, prompts: list[str], labels: dict[str, list[bool]]) -> QualityPredictor:
        if not prompts:
            raise ValueError("no training prompts")
        self._feats = build_features()
        X = self._feats.fit_transform(prompts)  # noqa: N806
        for m in self.models:
            y = np.array(labels[m], dtype=int)
            if len(y) != len(prompts):
                raise ValueError(f"label count for {m} does not match prompts")
            if y.min() == y.max():  # always right or always wrong in training
                self._clf[m] = float(y[0])
            else:
                self._clf[m] = LogisticRegression(C=self.C, max_iter=3000).fit(X, y)
        return self

    def predict(self, prompts: list[str]) -> dict[str, np.ndarray]:
        if self._feats is None:
            raise RuntimeError("predictor is not fitted")
        X = self._feats.transform(prompts)  # noqa: N806
        out = {}
        for m, clf in self._clf.items():
            out[m] = np.full(len(prompts), clf) if isinstance(clf, float) else clf.predict_proba(X)[:, 1]
        return out


HOPELESS = 0.15  # if no model is predicted above this, a bigger model is unlikely to help


def pick(probs: dict[str, float], allowed: list[str], threshold: float, hopeless: float = HOPELESS) -> str:
    """Cheapest allowed model (allowed is cheapest-first) whose P(correct) >= threshold.

    If none clears the threshold, use the largest allowed model, unless every model is predicted below
    `hopeless`: then spending more buys nothing, so use the cheapest and let the caller flag it."""
    if not allowed:
        raise ValueError("no model is allowed for this prompt")
    for m in allowed:
        if probs[m] >= threshold:
            return m
    if max(probs[m] for m in allowed) < hopeless:
        return allowed[0]
    return allowed[-1]
