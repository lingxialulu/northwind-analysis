# Question 3: New Customers vs Existing Customers

## Question
Should Northwind prioritize acquiring new customers or growing revenue from existing customers?

## Why it matters
Winning new customers and growing existing ones need different budgets and different teams. Northwind should put its effort where growth has actually come from, without ignoring the risk of depending on too few customers.

## Approach
I split each quarter's revenue into new customers (the quarter of their first order) and existing customers (all later orders), and broke existing-customer growth into more customers ordering, more orders per customer, and bigger orders. I compared the same days year over year, as in Question 1, and treated Jul–Dec 1996 as a warm-up period because the data starts on Jul 4, 1996 (code: `Question3_customers.py`, chart: `Question3_customers.png`).

## Main finding
- **Almost all growth came from existing customers, mainly because they ordered more often.**

  | | Jul–Dec 1997 vs 1996 | Jan 1 – May 6, 1998 vs 1997 |
  |---|---|---|
  | Revenue growth | +$123K | +$240K |
  | From existing customers | $118.8K (96%) | $237.8K (99%) |
  | From new customers | $4.6K (4 customers) | $2.0K (1 customer) |
  | Orders per customer | +24% (2.3 → 2.9) | +70% (2.0 → 3.3) |
  | Customers ordering | +12% | +21% |
  | Average order value | +13% | +6% |

- **Acquisition has nearly stopped.** New customers per quarter fell from 10 in Q1 1997 to 8, 3, 1 and 1, and none so far in Q2 1998. 89 of the 91 customers in the database have already ordered.
- **New customers are worth less, so far.** Customers won in 1997 or later spend a median of $1,309 per quarter after their first quarter, against $1,827 for customers already buying in 1996.
- **Some known customers are not buying.** 5 customers have not ordered in the last 6 months (they brought in $36.5K over the whole period), and 2 have never ordered (FISSA, PARIS).
- **Limitations:**
  - The data has no marketing costs and no list of potential customers. So "acquisition has dried up" may mean Northwind stopped trying, not that no customers are left to win.
  - The comparison of customer value is unfair to new customers: they have had less time to grow, and the 1996 customers include the long-standing large accounts.
  - Customers first seen in Jul–Dec 1996 may have been buying before the data starts, so 1996 is not used to judge acquisition.
  - Q2 1998 covers only Apr 1 – May 6. Its $142K is a faster pace than any full quarter, not a drop.

## Business implication
- **Prioritize growing existing customers**, especially how often they order, since that is what has driven growth. For example, offer reorder reminders or standing orders to the customers who already order regularly.
- **Win back the 5 lapsed customers and the 2 who never ordered.** They are known contacts and the cheapest revenue to recover.
- **Keep a small acquisition effort rather than dropping it.** With almost no new customers coming in, Northwind depends entirely on its current 89 accounts. A targeted pilot, such as the Sweden pilot from Question 1, keeps some new customers coming in without a large budget.
