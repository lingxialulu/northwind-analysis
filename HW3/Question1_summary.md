# Question 1: Overlooked High-Potential Markets

## Question
Which high-potential markets is Northwind overlooking?

## Why it matters
Northwind's revenue is concentrated in a few large markets (USA, Germany, Brazil, France). Markets that are growing fast but have few customers could be cheap places to expand. But if their growth comes from one account, putting money into them would be a mistake.

## Approach
I counted a country as an overlooked high-potential market if it has fewer customers than the typical country but grew revenue faster than most, without losing customers. I ran this test twice, comparing Jul–Dec 1997 with 1996 and Jan–May 1998 with 1997, and only trusted countries that passed both times (code: `Question1_markets.py`, chart: `Question1_markets.png`).

## Main finding
- **Most markets that look like opportunities have only 1–3 customers**, so their growth swings a lot from one period to the next. The data cannot prove that any market is truly overlooked.
- **Only Sweden qualifies in both periods.** It has just 2 customers, but both grew in both periods:
  - Berglunds snabbköp: $4,324 → $7,949 (Jul–Dec)
  - Folk och fä HB: $497 → $13,644 (Jan–May)
- **The other picks did not last.** Norway (−53%), Belgium (−31%) and Ireland (+32%, below the median) failed the Jul–Dec test. Denmark qualified in Jul–Dec, then fell 67% in early 1998. With 1–2 customers, growth comes and goes.
- **Spain grew in both periods (+95% and +2,274%), but mainly through one customer.** Godos Cocina Típica drove 89% of the early-1998 increase, even though the number of active customers rose from 1 to 4.

## Business implication
None of the overlooked markets is backed by strong evidence yet.
- **USA, Germany and Brazil remain the main revenue source and should stay the priority.** Together they bring in about 46% of all revenue ($581K of $1.27M), and all three grew in both periods:
  - USA: +91% (Jul–Dec) and +186% (Jan–May)
  - Germany: +88% and +159%
  - Brazil: +21% and +304%. Brazil's Jul–Dec growth was below the median.
- **Sweden: run a small pilot rather than a big investment.** For example, approach a few new Swedish customers and promote the products the current two are buying more of. Scale up only if new accounts start ordering.
- **Spain** is worth watching as a market where Northwind already has 5 accounts. Its next step is to grow the other four accounts so it doesn't depend on Godos Cocina Típica.
