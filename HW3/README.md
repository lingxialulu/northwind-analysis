# Northwind Traders: Three Business Questions

An analysis of the Northwind sample database (830 orders, Jul 1996 – May 1998) that answers three questions for a manager:

1. **Which high-potential markets is Northwind overlooking?**
2. **Which products should Northwind bundle to increase order value?**
3. **Should Northwind prioritize acquiring new customers or growing revenue from existing customers?**

The results are presented on a single webpage in [`website/index.html`](website/index.html).

## Repository contents

| File | What it is |
|---|---|
| `Northwind.xlsx` | Source data: 8 sheets (Orders, Orders Details, Customers, Product, Categories, Employees, Shippers, Suppliers) |
| `Question1_markets.py` | Analysis code for Question 1; writes `Question1_markets.png` |
| `Question2_bundles.py` | Analysis code for Question 2; writes `Question2_bundles.png` |
| `Question3_customers.py` | Analysis code for Question 3; writes `Question3_customers.png` |
| `Question1_summary.md`, `Question2_summary.md`, `Question3_summary.md` | Written summary of each question |
| `website/` | The webpage (`index.html`) and copies of the three charts in `website/images/` |
| `requirements.txt` | Python packages and the versions used |

## Setup

The analysis was run with **Python 3.9.6** on macOS. Install the packages with:

```bash
pip3 install -r requirements.txt
```

This installs:

| Package | Version | Used for |
|---|---|---|
| pandas | 2.3.3 | Reading the Excel file and all calculations |
| openpyxl | 3.1.5 | Lets pandas read `.xlsx` files |
| matplotlib | 3.9.4 | Charts |
| numpy | 2.0.2 | Installed with pandas; also used directly in Question 2 |

Run every command below from the project folder (the one containing `Northwind.xlsx`). Each script takes a few seconds.

## Reproducing each question

### Question 1: Overlooked high-potential markets

```bash
python3 Question1_markets.py
```

**Writes:** `Question1_markets.png`.

**Prints, for each of the two comparisons** (Jul 4 – Dec 31, 1997 vs 1996, and Jan 1 – May 6, 1998 vs 1997):
- a per-country table: customers, revenue in each period, revenue growth, active-customer growth, the top customer's share of the increase, and whether the country qualifies
- a robustness check: the countries that qualify in each comparison and in both (**Sweden**)
- a per-customer breakdown of revenue and orders for Sweden and Spain

The webpage numbers for Norway, Belgium, Ireland, Denmark, Spain, USA, Germany and Brazil all come from the two per-country tables. The 46% revenue share for USA, Germany and Brazil comes from the snippet under [Webpage headline numbers](#webpage-headline-numbers).

### Question 2: Product bundles

```bash
python3 Question2_bundles.py
```

**Writes:** `Question2_bundles.png`.

**Prints:**
- the 48 candidate product pairs, with lift, orders in each half of the data, average order value and value index
- how many pairs hold up in both halves (20) and how many are recommended (3)
- the table of 28 category pairs (none has lift above 1)
- the three recommended bundles
- the **price check** table: for each recommended pair, orders with both products, only A and only B, split into the pair's own lines and the rest of the order

The "roughly $400–900" added by a cross-sell comes from the `avg_A+B_lines` column of the price check for the "A only" and "B only" rows. That column shows what each product is worth in an order when bought on its own.

### Question 3: New vs existing customers

```bash
python3 Question3_customers.py
```

**Writes:** `Question3_customers.png`.

**Prints:**
- revenue by quarter from new and existing customers, with new customers acquired per quarter
- the growth drivers for both comparisons: revenue from new and existing customers, and the change in customers ordering, orders per customer and average order value
- revenue per customer per quarter for customers first seen in 1996 and customers won in 1997 or later
- headroom: customers who never ordered (FISSA, PARIS) and customers with no order in the last 6 months

### Webpage headline numbers

The webpage's intro facts (830 orders, 91 customers in 21 countries, 77 products, $1.27M revenue) and the USA + Germany + Brazil share come from this snippet:

```bash
python3 - <<'EOF'
import pandas as pd

sheets = pd.read_excel("Northwind.xlsx", sheet_name=None)
orders, details = sheets["Orders"], sheets["Orders Details"]
customers, products = sheets["Customers"], sheets["Product"]

details["Revenue"] = details["UnitPrice"] * details["Quantity"] * (1 - details["Discount"])
revenue = details["Revenue"].sum()
print(f"Orders: {orders['OrderID'].nunique()}")
print(f"Customers: {customers['CustomerID'].nunique()} in {customers['Country'].nunique()} countries")
print(f"Products: {products['ProductID'].nunique()}")
print(f"Revenue: ${revenue:,.0f}")
print(f"Order dates: {orders['OrderDate'].min():%Y-%m-%d} to {orders['OrderDate'].max():%Y-%m-%d}")

by_country = (details.merge(orders[["OrderID", "CustomerID"]], on="OrderID")
              .merge(customers[["CustomerID", "Country"]], on="CustomerID")
              .groupby("Country")["Revenue"].sum())
top3 = by_country[["USA", "Germany", "Brazil"]].sum()
print(f"USA + Germany + Brazil: ${top3:,.0f} ({top3 / revenue:.0%} of revenue)")
EOF
```

Expected output:

```
Orders: 830
Customers: 91 in 21 countries
Products: 77
Revenue: $1,265,793
Order dates: 1996-07-04 to 1998-05-06
USA + Germany + Brazil: $581,384 (46% of revenue)
```

## Updating the webpage

The webpage uses copies of the charts. After rerunning the scripts, copy the new charts into the website folder:

```bash
cp Question1_markets.png Question2_bundles.png Question3_customers.png website/images/
```

The text on the webpage is written by hand from the three `Question*_summary.md` files, so it does not update automatically if the results change.

To view the page locally, open `website/index.html` in a browser. To publish it, upload the `website` folder to a static host such as Netlify.

## Definitions and method notes

Each script starts with a `# Definitions` comment block that defines its terms, such as "overlooked high-potential", "holds up", "value index" and "warm-up". Key choices:

- **Revenue** = UnitPrice × Quantity × (1 − Discount), using the price charged in Orders Details.
- **Year-over-year comparisons** use the same days in both years, because the data starts on Jul 4, 1996 and ends on May 6, 1998.
- **Small samples:** countries with 3 or fewer customers are flagged, and product pairs need at least 4 orders from at least 2 customers.
- **Robustness:** a result counts only if it holds in both comparison periods (Questions 1 and 3) or both halves of the data (Question 2).
