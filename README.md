# NZ Election Tracker 2026

A standalone page that puts every published poll for the 7 November 2026 New Zealand general election on one trend line per party, takes out each pollster's lean, runs the election 20,000 times, and shows the chance each side can form a government. Betting and prediction markets sit on their own tab and never feed the forecast.

## How it fits together

| Part | Where | What it does |
| --- | --- | --- |
| Website | `index.html`, `assets/`, hosted on Vercel | Plain HTML, CSS and JavaScript with d3 and the fonts served from this repo. No build step: Vercel serves the files as they are. |
| Data | `data/*.json` | The twelve files the page reads: chances, trend, polls, latest, leans_wide, eday, summary, history, parliament, maori, close_seats, markets. |
| Model | `model/` (not published) | `polls.csv` holds every poll, `markets_in.json` the market rows, `history.json` each day's result. `model.py` fits the trends and runs the simulations; `export.py` writes the page's files. |
| Morning refresh | A scheduled task in Claude, 6:57am NZ until election day | Adds new polls and market readings, runs `model/refresh.sh`, commits the new `data/` files and pushes, which redeploys the site. Sends no notifications. |

## Refreshing by hand

1. Add the poll to `model/polls.csv`: `start,end,pollster,n,NAT,LAB,GRN,ACT,NZF,TPM,OPP,OTH`, fieldwork dates as YYYY-MM-DD, figures as published, `n` 1000 if not published, `OTH` blank.
2. Run `model/refresh.sh` (needs Python 3 and numpy; about 30 seconds).
3. Commit `data/`, `model/polls.csv` and `model/history.json`, then push.

## The market rule

A market price only counts if it is a bookmaker's fixed-odds price with the margin taken out, or a prediction market or exchange with at least US$250,000 traded and buy and sell prices within 2 cents. Everything else is listed as not counted, with the reason.
