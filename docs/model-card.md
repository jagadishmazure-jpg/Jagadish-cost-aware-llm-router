# Model card: quality predictor and router

**What it is.** Three logistic-regression classifiers, one per model tier, each predicting "this model
will answer this prompt correctly". The router takes the cheapest allowed tier at or above a threshold.

**Training data.** 351 training tasks with measured, code-scored answers from each model (synthetic
logistics tasks for the fictional Lumenfield Freight). See the [data card](data-card.md).

**Features.** Word 1-2 gram and character 3-5 gram TF-IDF, plus prompt-shape features (length, digit
count, question type). The prompt only: the predictor never sees a model's answer.

**Measured on 120 test tasks.** AUC 0.9735<!-- m:predictor/qwen2.5-0.5b/auc --> (small), 0.9868<!-- m:predictor/qwen2.5-1.5b/auc --> (medium),
0.9313<!-- m:predictor/phi-3.5-mini/auc --> (large). Brier 0.0627<!-- m:predictor/qwen2.5-0.5b/brier -->, 0.0261<!-- m:predictor/qwen2.5-1.5b/brier -->,
0.0955<!-- m:predictor/phi-3.5-mini/brier -->. Threshold 0.8<!-- m:threshold/chosen --> chosen on validation.

**Intended use.** A starting point for routing structured, checkable requests between model tiers.

**Not for.** Open-ended writing, other languages, or models it was not trained on. A new model or a
new task type needs new measured runs and a retrain.

**Ethics and safety.** Personal data never reaches the large tier, whatever the predictor says. The
predictor only picks among models a policy already allows.
