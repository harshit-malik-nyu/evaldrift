# What data was reachable, and what that decided

Before any code was written, every candidate data source was probed from CI and
the results committed. That order matters: designing against data you have not
touched is how a project discovers halfway through that its central measurement
is impossible.

## What was wanted

Per-item results — which specific questions each model version got right —
across successive versions of the same model. That is the only data that
directly demonstrates churn: two runs scoring identically while disagreeing on
a large share of items.

## What was found

| Source | Result |
|---|---|
| HuggingFace API | reachable |
| **DOVE** (250M per-instance predictions) | **gated** — `"gated": "auto"`, needs an account token |
| DOVE_Lite | gated, same |
| HELM classic | reachable, but a JavaScript application rather than data |
| HELM public GCS bucket | exists and is public; the path guessed was wrong |
| GSM8K test split (GitHub) | **reachable — 1,319 items, downloaded** |

## What that decided

The gated per-item corpora would have been convenient. Their absence made the
project stronger rather than weaker, for a reason worth stating.

The headline finding — that most quoted benchmarks cannot resolve a two-point
change — follows from **published split sizes alone**. It needs no model
outputs, which means it cannot be contested on the grounds that the wrong model
was measured, the wrong prompt was used, or the results are stale. It is
arithmetic on numbers every benchmark's authors published themselves.

The churn measurement, which does need per-item data, was rebuilt around
running the identical model twice over a fixed GSM8K sample. That turns out to
be the better design regardless of access: it measures the **noise floor** with
ground truth for free, because the model did not change between passes and
every flipped item is therefore a false signal by construction.

A convenient dataset would have produced a weaker project.

## Raw probe output

```
# per-item eval data probe
run_at=2026-09-18T01:59:01Z

HTTP=200 bytes=281203  DOVE_Lite metadata
   head: {"_id":"67be44a2e30b2f126c5d8bc5","id":"nlphuji/DOVE_Lite","author":"nlphuji","sha":"bc1129e223f3f48f0e4180694cde261e02da685e","lastModified":"2025-08-14T15:22:46.000Z","private":false,"gated":"auto",

HTTP=200 bytes=280688  DOVE metadata
   head: {"_id":"67b7b135f0c9d7a3536ae7dd","id":"nlphuji/DOVE","author":"nlphuji","sha":"b552dd99125a2d7b20a902c6e8fd303cf296b5a8","lastModified":"2025-08-14T10:14:01.000Z","private":false,"gated":"auto","disa

HTTP=404 bytes=9  HF datasets-server
   head: Not Found

HTTP=200 bytes=2456  HF search: helm
   head: [{"_id":"641a36394097fa34bd332e4a","id":"pzalavad/HelmetDataset","author":"pzalavad","disabled":false,"gated":false,"lastModified":"2023-03-25T00:49:25.000Z","likes":0,"trendingScore":0,"private":fals

HTTP=200 bytes=1295  HELM classic
   head: <!doctype html> <html lang="en">   <head>     <meta charset="UTF-8" />     <link rel="icon" type="image/svg+xml" href="https://crfm.stanford.edu/helm/helm.svg" />     <meta name="viewport" content="wi

HTTP=404 bytes=227  HELM public bucket
   head: <?xml version='1.0' encoding='UTF-8'?><Error><Code>NoSuchKey</Code><Message>The specified key does not exist.</Message><Details>No such object: crfm-helm-public/lite/benchmark_output/runs/v1.0.0/run_s

HTTP=200 bytes=55868  MMLU dataset
   head: {"_id":"621ffdd236468d709f181e5e","id":"cais/mmlu","author":"cais","sha":"c30699e8356da336a370243923dbaf21066bb9fe","lastModified":"2024-03-08T20:36:26.000Z","private":false,"gated":false,"disabled":f

HTTP=403 bytes=9801  control: public web
   head: <html>   <head>     <style global>body{font-family:Arial,Helvetica,sans-serif}.container{align-items:center;display:flex;flex-direction:column;gap:2rem;height:100%;justify-content:center;width:100%}@k
```
