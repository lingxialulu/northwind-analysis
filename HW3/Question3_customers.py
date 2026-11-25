"""Compare revenue from new and existing Northwind customers.

Prints growth tables and saves Question3_customers.png.
"""

# Definitions
# New customer      = revenue from a customer's first-order quarter.
# Existing customer = revenue from all later quarters.
# Warm-up           = Jul - Dec 1996. Orders start on 1996-07-04, so a
#                     customer whose first order falls in 1996 may have
#                     been buying before; they are treated as the
#                     starting customer base, not as truly new.
# Existing-customer growth is split into three drivers:
#     revenue = active customers x orders per customer x average order value
# using the same two comparisons as Question 1 (same days year over year).
#
# Output: tables printed to the console, and Question3_customers.png.

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

HERE = Path(__file__).resolve().parent
DATA = HERE / "Northwind.xlsx"
CHART = HERE / "Question3_customers.png"
WARMUP_END = pd.Timestamp("1996-12-31")
LAPSED_DAYS = 182  # no order in this many days before the last order date = lapsed

COMPARISONS = [
    ("Jul 4 - Dec 31, 1997 vs 1996", ("1996-07-04", "1996-12-31"), ("1997-07-04", "1997-12-31")),
    ("Jan 1 - May 6, 1998 vs 1997", ("1997-01-01", "1997-05-06"), ("1998-01-01", "1998-05-06")),
]

COLOR_EXISTING = "#2a6f97"
COLOR_NEW = "#e07a1f"
COLOR_LINE = "#333333"


def load():
    """Load Northwind data as one row per order.

    Args:
        None.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: ``orders``, indexed by
            OrderID with CustomerID, OrderDate, value, quarter,
            first_order, first_quarter and type ("new" in the
            customer's first-order quarter, else "existing"); and the
            raw Customers sheet.
    """
    sheets = pd.read_excel(DATA, sheet_name=["Orders", "Orders Details", "Customers"])
    details = sheets["Orders Details"]
    revenue = (details["UnitPrice"] * details["Quantity"] * (1 - details["Discount"]))
    value = revenue.groupby(details["OrderID"]).sum().rename("value")

    orders = sheets["Orders"].set_index("OrderID")[["CustomerID", "OrderDate"]].join(
        value, how="inner"
    )
    assert len(orders) == sheets["Orders"]["OrderID"].nunique(), "orders without lines"

    orders["quarter"] = orders["OrderDate"].dt.to_period("Q")
    orders["first_order"] = orders.groupby("CustomerID")["OrderDate"].transform("min")
    orders["first_quarter"] = orders["first_order"].dt.to_period("Q")
    orders["type"] = (orders["quarter"] == orders["first_quarter"]).map(
        {True: "new", False: "existing"}
    )
    return orders, sheets["Customers"]


def quarterly(orders):
    """Summarize new and existing customer revenue by quarter.

    Args:
        orders (pd.DataFrame): Orders from ``load``.

    Returns:
        pd.DataFrame: One row per quarter with existing and new
            revenue, new customers, active customers, order count, and
            new revenue as a percent of the total.
    """
    table = orders.pivot_table(
        index="quarter", columns="type", values="value", aggfunc="sum"
    ).reindex(columns=["existing", "new"]).fillna(0)
    firsts = orders.drop_duplicates("CustomerID")["first_quarter"].value_counts()
    table["new_customers"] = firsts.reindex(table.index).fillna(0).astype(int)
    table["active_customers"] = orders.groupby("quarter")["CustomerID"].nunique()
    table["orders"] = orders.groupby("quarter").size()
    table["new_share_pct"] = table["new"] / (table["new"] + table["existing"]) * 100
    return table


def window(orders, dates):
    """Return orders dated inside a window.

    Args:
        orders (pd.DataFrame): Orders with an OrderDate column.
        dates (tuple[str, str]): Start and end dates, both inclusive.

    Returns:
        pd.DataFrame: Rows of ``orders`` inside the window.
    """
    start, end = pd.Timestamp(dates[0]), pd.Timestamp(dates[1])
    return orders[(orders["OrderDate"] >= start) & (orders["OrderDate"] <= end)]


def drivers(orders):
    """Split revenue growth into new and existing customer drivers.

    Customers whose first order is on or after the later window's
    start are new; others ordering then are existing. Existing revenue
    is split into active customers, orders per customer and average
    order value, each compared with the whole earlier window.

    Args:
        orders (pd.DataFrame): Orders from ``load``.

    Returns:
        pd.DataFrame: One row per comparison in ``COMPARISONS`` with
            revenue in each window, the change from new and existing
            customers, and each driver's values and percent change.
    """
    rows = []
    for label, prev_dates, cur_dates in COMPARISONS:
        prev = window(orders, prev_dates)
        cur = window(orders, cur_dates)
        is_new = cur["first_order"] >= pd.Timestamp(cur_dates[0])
        new, existing = cur[is_new], cur[~is_new]

        def factors(df):
            """Return the three revenue drivers for a set of orders.

            Args:
                df (pd.DataFrame): Orders in one window.

            Returns:
                tuple[int, float, float]: Distinct customers, orders
                    per customer, and mean order value.
            """
            customers =df["CustomerID"].nunique()
            return customers, len(df) / customers, df["value"].mean()

        p_cust, p_freq, p_aov = factors(prev)
        e_cust, e_freq, e_aov = factors(existing)
        change = cur["value"].sum() - prev["value"].sum()
        rows.append({
            "comparison": label,
            "revenue_prev": prev["value"].sum(),
            "revenue_cur": cur["value"].sum(),
            "revenue_change": change,
            "from_new_customers": new["value"].sum(),
            "from_existing_customers": existing["value"].sum() - prev["value"].sum(),
            "new_customers": new["CustomerID"].nunique(),
            "active_customers_prev": p_cust,
            "active_existing_cur": e_cust,
            "active_change_pct": (e_cust / p_cust - 1) * 100,
            "orders_per_customer_prev": p_freq,
            "orders_per_customer_cur": e_freq,
            "frequency_change_pct": (e_freq / p_freq - 1) * 100,
            "avg_order_prev": p_aov,
            "avg_order_cur": e_aov,
            "order_value_change_pct": (e_aov / p_aov - 1) * 100,
        })
    return pd.DataFrame(rows).set_index("comparison")


def customer_value(orders):
    """Compare revenue per customer-quarter across customer groups.

    Groups are customers first seen in 1996, customers won from 1997
    in their first quarter, and the same customers in later quarters.
    The first and third groups use full quarters Q1 1997 - Q1 1998.

    Args:
        orders (pd.DataFrame): Orders from ``load``.

    Returns:
        pd.DataFrame: One row per group with customers,
            customer-quarters, and mean and median revenue per
            customer-quarter.
    """
    full = orders[(orders["quarter"] >= pd.Period("1997Q1")) & (orders["quarter"] <= pd.Period("1998Q1"))]
    base = full[full["first_order"] <= WARMUP_END]
    won = full[(full["first_order"] > WARMUP_END) & (full["type"] == "existing")]
    first_q = orders[(orders["first_order"] > WARMUP_END) & (orders["type"] == "new")]

    def per_customer_quarter(df):
        """Summarize revenue per customer per quarter.

        Args:
            df (pd.DataFrame): Orders for one customer group.

        Returns:
            pd.Series: Customers, customer-quarters, and mean and
                median revenue per customer-quarter.
        """
        by_cq =df.groupby(["CustomerID", "quarter"])["value"].sum()
        return pd.Series({
            "customers": df["CustomerID"].nunique(),
            "customer_quarters": len(by_cq),
            "avg_revenue_per_quarter": by_cq.mean(),
            "median_revenue_per_quarter": by_cq.median(),
        })

    return pd.DataFrame({
        "Starting base (first order in 1996)": per_customer_quarter(base),
        "Won in 1997+: first quarter": per_customer_quarter(first_q),
        "Won in 1997+: later quarters": per_customer_quarter(won),
    }).T


def headroom(orders, customers):
    """Find known customers who never ordered or have lapsed.

    Args:
        orders (pd.DataFrame): Orders from ``load``.
        customers (pd.DataFrame): Customers sheet.

    Returns:
        dict[str, int | float | list[str]]: Customers in the database
            and who ordered, never-ordered and lapsed CustomerIDs, and
            lapsed customers' total revenue. Lapsed means no order in
            the ``LAPSED_DAYS`` before the last order date.
    """
    last_date = orders["OrderDate"].max()
    last_order = orders.groupby("CustomerID")["OrderDate"].max()
    lapsed = last_order[last_order < last_date - pd.Timedelta(days=LAPSED_DAYS)]
    never = sorted(set(customers["CustomerID"]) - set(orders["CustomerID"]))
    return {
        "customers_in_database": customers["CustomerID"].nunique(),
        "customers_who_ordered": orders["CustomerID"].nunique(),
        "never_ordered": never,
        "lapsed_6_months": sorted(lapsed.index),
        "lapsed_revenue_total": orders[orders["CustomerID"].isin(lapsed.index)]["value"].sum(),
    }


def plot(table, last_date):
    """Draw quarterly revenue by customer type and save the chart.

    Bars stack existing and new customer revenue; a line on a second
    axis shows new customers per quarter.

    Args:
        table (pd.DataFrame): Quarterly table from ``quarterly``.
        last_date (pd.Timestamp): Last order date; the final quarter
            is marked partial if this is before its end.

    Returns:
        None. Saves the figure to ``CHART``.
    """
    labels = [f"Q{q.quarter} {q.year}" for q in table.index]
    x = range(len(table))
    fig, ax = plt.subplots(figsize=(12, 7))

    warmup = [i for i, q in enumerate(table.index) if q.end_time <= WARMUP_END + pd.Timedelta(days=1)]
    if warmup:
        ax.axvspan(min(warmup) - 0.5, max(warmup) + 0.5, color="#eeeeee", zorder=0)
        ax.text((min(warmup) + max(warmup)) / 2,
                table[["existing", "new"]].sum(axis=1).max() / 1000 * 1.17,
                "Warm-up: data starts Jul 4, 1996,\nso 'new' here may be earlier customers",
                ha="center", va="top", fontsize=8.5, color="#555555")

    ax.bar(x, table["existing"] / 1000, color=COLOR_EXISTING, alpha=0.85, label="Existing customers")
    ax.bar(x, table["new"] / 1000, bottom=table["existing"] / 1000, color=COLOR_NEW,
           alpha=0.85, label="New customers (first-order quarter)")

    partial = table.index[-1]
    if last_date < partial.end_time.normalize():
        labels[-1] += f"\n(partial: to {last_date:%b} {last_date.day})"
        ax.bar(len(table) - 1, (table["existing"].iloc[-1] + table["new"].iloc[-1]) / 1000,
               fill=False, hatch="//", edgecolor="white", linewidth=0)

    for i, (_, row) in enumerate(table.iterrows()):
        total = (row["existing"] + row["new"]) / 1000
        ax.text(i, total + 4, f"${total:,.0f}K\n{row['new_share_pct']:.0f}% new",
                ha="center", va="bottom", fontsize=8.5)

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Revenue ($ thousands)")
    ax.set_ylim(0, table[["existing", "new"]].sum(axis=1).max() / 1000 * 1.2)
    ax.grid(axis="y", alpha=0.2)

    ax2 = ax.twinx()
    ax2.plot(list(x), table["new_customers"], color=COLOR_LINE, marker="o", lw=1.8)
    for i, n in enumerate(table["new_customers"]):
        ax2.annotate(str(n), (i, n), xytext=(0, 7), textcoords="offset points",
                     ha="center", fontsize=9, fontweight="bold", color=COLOR_LINE)
    ax2.set_ylabel("New customers acquired in the quarter")
    ax2.set_ylim(0, table["new_customers"].max() * 1.25)

    ax.legend(
        handles=[Patch(color=COLOR_EXISTING, alpha=0.85), Patch(color=COLOR_NEW, alpha=0.85),
                 Line2D([], [], color=COLOR_LINE, marker="o")],
        labels=["Revenue from existing customers", "Revenue from new customers (first-order quarter)",
                "New customers acquired (right axis)"],
        loc="upper left", bbox_to_anchor=(0.36, 1), fontsize=9,
    )
    ax.set_title("Northwind revenue by quarter: existing vs new customers")
    fig.text(0.01, 0.01,
             "New customer revenue = orders in the quarter of a customer's first order. "
             "Existing = all later orders. Revenue = UnitPrice x Quantity x (1 - Discount).",
             fontsize=8, color="#444444")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(CHART, dpi=150)
    plt.close(fig)


def main():
    """Run the customer analysis, print the tables, and save the chart.

    Args:
        None.

    Returns:
        None. Prints tables to stdout and writes ``CHART``.
    """
    orders, customers = load()
    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 30)

    table = quarterly(orders)
    print("=== Revenue by quarter ===")
    print(table.round(1).to_string(), "\n")

    print("=== Growth drivers (same days year over year) ===")
    print(drivers(orders).round(1).T.to_string(), "\n")

    print("=== Revenue per customer per quarter (full quarters Q1 1997 - Q1 1998) ===")
    print(customer_value(orders).round(0).to_string(), "\n")

    room = headroom(orders, customers)
    print("=== Headroom among known customers ===")
    for key, val in room.items():
        if isinstance(val, list):
            print(f"{key}: {len(val)} {val}")
        else:
            print(f"{key}: {val:,.0f}")

    plot(table, orders["OrderDate"].max())
    print(f"\nChart saved to {CHART}")


if __name__ == "__main__":
    main()
