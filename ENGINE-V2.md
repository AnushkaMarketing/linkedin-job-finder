# Engine 2: requirement reasoning and local feedback learning

This release improves deterministic intelligence and adds a trainable local preference ranker. It does **not** claim a newly trained foundation model, hiring-outcome accuracy, or comprehensive labour-market coverage.

## New reasoning

- Curated marketing, content, software, data and design skill aliases and directional transferable relationships. Related skills remain partial evidence. The ontology is curated in `backend/ontology.py`, not a copy of the complete ESCO taxonomy.
- Required, preferred and mentioned groups use weights 3:1:2. Alternatives such as “Python or Java” need one match; “and SQL” creates a separate requirement. Explicitly negated skill requirements are excluded. The original evidence sentence accompanies every group. Language interpretation remains heuristic; complex clauses should be reviewed in the source.
- BM25 title/profile retrieval selects the analysis pool when discovery exceeds 2,500 candidates. Detailed factor ranking and geographic restrictions still determine eligibility and ordering.
- Majority missing must-have groups cap priority at 55. Personalization cannot exceed this cap. CV fit is never rewritten by feedback.
- Source-age questions, possible candidate-payment language, missing salary/office prompts and evidence-coverage warnings explain what to investigate. These are signals, not legitimacy determinations.
- Shortlist gap counts identify skills that occur in multiple shortlisted requirements, with no claim about the wider job market.

## Training

Open a real result and choose **Relevant to me** or **Not relevant**. The server derives features from the stored result; clients cannot submit arbitrary features. Demo jobs are excluded. Relabelling replaces the old vote.

Eight labels with at least three of each class activate a class-balanced, L2-regularized logistic model. It runs deterministic batch gradient descent over the most recent 300 labels. Inputs are centered factor scores and evidence coverage, not names or protected characteristics. Missing factors are neutral. Feedback is scoped to the matching profile fingerprint; changing matching profile fields starts a new context.

The trained preference changes priority by at most ±4 points on subsequent searches. It never removes hard location/work-mode constraints, fabricates qualifications or modifies verification. Personalization is a preference estimate, not a probability of employment. No model is active during cold start.

Labels are encrypted with the rest of the workspace. Delete all data in settings to erase labels, or call `DELETE /api/learning` with the local token to reset only the active profile's labels.

## Motion design

A 200-point canvas maps experience, role alignment, evidence and shortlist. Points respond to the pointer, with spring return and flowing connections. Card hover motion uses the existing Motion dependency. Pause, reduced-motion settings, offscreen detection and background-tab suspension control animation. Visual animation is illustrative and does not impersonate live source activity.

## Research references

- [Sentence Transformers retrieve-and-rerank architecture](https://www.sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html): reviewed the separation of candidate retrieval and deeper ranking. This implementation uses local BM25 and explicit factor reasoning; pretrained embedding/cross-encoder models are **not** installed or silently downloaded.
- [ESCO taxonomy research](https://arxiv.org/abs/2305.12092): reviewed taxonomy-aware job representations. No claim that this app implements the paper's model or its measured performance.
- [Motion reduced-motion documentation](https://motion.dev/docs/react-use-reduced-motion): used for user preference support. No external skill packages or unreviewed repository installers were necessary.

## Evaluation boundaries

Automated tests cover OR/AND grouping, negation, required/preferred weights, BM25 relevance, cold start, deterministic bounded training, profile isolation, feedback replacement, priority caps and the existing pipeline/security tests. Browser tests cover animation frame changes, pause, reduced motion, the complete user workflow and mobile overflow. These are regression checks on curated cases, not a representative accuracy benchmark. Real relevance labels and a separately held-out evaluation set are needed before making statistical accuracy claims.
