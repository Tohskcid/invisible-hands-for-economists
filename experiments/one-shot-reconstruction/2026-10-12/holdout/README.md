# Evaluator-only holdout

Do not expose this directory, curator messages, or temporary source files to reconstruction workers. This is an answer-bearing evaluation artifact. No full article text is stored in the repository.

The AER benchmark's question is recorded in [aer-card-krueger-1994.json](aer-card-krueger-1994.json). Its published numbers were read from the [author-hosted final article](https://davidcard.berkeley.edu/papers/njmin-aer.pdf) and visually checked on pages 780 and 783. They are **published targets**, not independent reestimates.

The [author's public archive](https://davidcard.berkeley.edu/data_sets/njmin.zip) downloads without login, and the [author README](https://davidcard.berkeley.edu/readme/njmin-readme.txt) identifies its contents. The archive includes answer-bearing `check.sas`: raw-data discovery can inadvertently reveal published analysis choices. A worker should inventory the archive, acquire data and codebook, and log any analysis-code access. The archive alone does not support every block in the published paper.

Published coefficients, author-program results, worker reestimates, and evaluator reestimates must have separate provenance. Never silently replace a published target with a computed value. The survey-only benchmark tests numerical research reconstruction and honest disclosure of missing inputs; it does not establish scientific discovery or absence of model-training memory.

Original PDFs, extracted full text and rendered source pages stay in `/private/tmp`. The author-hosted source files are publicly retrievable, but no unrestricted redistribution license is inferred.

The Econometrica benchmark is recorded in [econometrica-rubinstein-1982.json](econometrica-rubinstein-1982.json), checked against all pages of the [author-hosted article](https://arielrubinstein.tau.ac.il/papers/11.pdf). Its criterion includes the general interval characterization, additive fixed costs, unequal geometric discounts, and the equal-cost delayed-equilibrium exception. The JSON separates published mathematical facts from curator-created numerical and constructive checks. Only analytic proof review is available; no machine-verified Lean proof is claimed.
