"""Find product pairs Northwind could bundle to raise order value.

Prints pair and category tables and saves Question2_bundles.png.
"""

# Definitions
# Bundle candidate   = two active (not discontinued) products bought
#                      together in at least 4 orders, by at least 2
#                      different customers, with lift > 1 (more often
#                      than chance).
# Holds up           = lift > 1 and at least 2 orders together in BOTH
#                      halves of the data (orders split at the median
#                      order date, 415 orders each).
# Raises order value = the median "value index" of orders containing
#                      the pair is above 1. Value index = order value /
#                      average value of all orders with the same number
#                      of products, so big orders don't look good just
#                      because they contain more products.
# Recommended bundle = holds up and raises order value.
#
# If no product pair holds up, category-level bundles become the
# recommendation. The category-level table is always printed for
# comparison.
#
# Output: tables printed to the console, and Question2_bundles.png.

from itertools import combinations
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

HERE = Path(__file__).resolve().parent
DATA = HERE / "Northwind.xlsx"
CHART = HERE / "Question2_bundles.png"
MIN_ORDERS = 4          # pair must appear in at least this many orders
MIN_CUSTOMERS = 2       # ... from at least this many customers
MIN_ORDERS_PER_HALF = 2 # ... and this many orders in each half of the data

COLOR_RECOMMENDED = "#e07a1f"
COLOR_HOLDS = "#2a6f97"
COLOR_FADED = "#9aa5ad"


def load():
    """Load Northwind sheets as order lines, orders and products.

    ``value_index`` is an order's value divided by the mean value of
    orders with the same number of products; ``half`` splits orders
    at the median order date.

    Args:
        None.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]: ``lines``, one
            row per order line with Revenue, CustomerID, OrderDate and
            CategoryName; ``orders``, indexed by OrderID with value,
            n_products, date, customer, half and value_index; and
            ``products``, indexed by ProductID with name, category,
            price and a boolean Discontinued.
    """
    sheets = pd.read_excel(
        DATA, sheet_name=["Orders", "Orders Details", "Product", "Categories"]
    )
    products = sheets["Product"][
        ["ProductID", "ProductName", "CategoryID", "Price", "Discontinued"]
    ].merge(sheets["Categories"][["CategoryID", "CategoryName"]], on="CategoryID")
    products["Discontinued"] = (
        products["Discontinued"].astype(str).str.lower().isin(["true", "1"])
    )
    products = products.set_index("ProductID")

    details = sheets["Orders Details"]
    lines = details.assign(
        Revenue=details["UnitPrice"] * details["Quantity"] * (1 - details["Discount"])
    ).merge(sheets["Orders"][["OrderID", "CustomerID", "OrderDate"]], on="OrderID")
    lines["CategoryName"] = lines["ProductID"].map(products["CategoryName"])
    assert lines["CategoryName"].notna().all(), "order lines with an unknown product"

    orders = lines.groupby("OrderID").agg(
        value=("Revenue", "sum"),
        n_products=("ProductID", "nunique"),
        date=("OrderDate", "first"),
        customer=("CustomerID", "first"),
    )
    median_date = orders["date"].median()
    orders["half"] = (orders["date"] >= median_date).map({False: "first", True: "second"})
    same_size_avg = orders.groupby("n_products")["value"].transform("mean")
    orders["value_index"] = orders["value"] / same_size_avg
    return lines, orders, products


def pair_table(lines, orders, item):
    """Count co-purchases, lift and order value for each item pair.

    Args:
        lines (pd.DataFrame): Order lines from ``load``.
        orders (pd.DataFrame): Orders from ``load``.
        item (str): Column defining an item, e.g. ``"ProductID"`` or
            ``"CategoryName"``.

    Returns:
        pd.DataFrame: One row per pair, indexed by (a, b) with a < b,
            with order and customer counts, lift, mean order value,
            median value index, per-half counts and lift, and
            ``holds_up`` and ``raises_value`` flags.
    """
    baskets = lines.groupby("OrderID")[item].apply(lambda s: sorted(set(s)))
    rows = [(oid, a, b) for oid, items in baskets.items() for a, b in combinations(items, 2)]
    pairs = pd.DataFrame(rows, columns=["OrderID", "a", "b"]).merge(
        orders, left_on="OrderID", right_index=True
    )

    table = pairs.groupby(["a", "b"]).agg(
        orders=("OrderID", "size"),
        customers=("customer", "nunique"),
        avg_order_value=("value", "mean"),
        value_index=("value_index", "median"),
    )

    item_orders = lines.merge(orders[["half"]], left_on="OrderID", right_index=True)

    def lift(counts, n_orders, freq):
        """Return observed over expected co-purchases for each pair.

        Args:
            counts (pd.Series): Orders containing each pair, aligned
                with ``table``.
            n_orders (int): Orders in the period.
            freq (pd.Series): Orders containing each item.

        Returns:
            numpy.ndarray: Lift per pair, in ``table`` row order.
        """
        a = table.index.get_level_values("a")
        b = table.index.get_level_values("b")
        expected = freq.reindex(a).to_numpy() * freq.reindex(b).to_numpy() / n_orders
        return counts.to_numpy() / expected

    freq_all = item_orders.groupby(item)["OrderID"].nunique()
    table["lift"] = lift(table["orders"], len(orders), freq_all)

    for half in ("first", "second"):
        in_half = item_orders[item_orders["half"] == half]
        counts = pairs[pairs["half"] == half].groupby(["a", "b"]).size()
        counts = counts.reindex(table.index).fillna(0)
        table[f"orders_{half}"] = counts
        table[f"lift_{half}"] = lift(
            counts, (orders["half"] == half).sum(),
            in_half.groupby(item)["OrderID"].nunique(),
        )

    table["holds_up"] = (
        (table["lift_first"] > 1) & (table["lift_second"] > 1)
        & (table["orders_first"] >= MIN_ORDERS_PER_HALF)
        & (table["orders_second"] >= MIN_ORDERS_PER_HALF)
    )
    table["raises_value"] = table["value_index"] > 1
    return table


def product_candidates(lines, orders, products):
    """Filter product pairs to bundle candidates and flag picks.

    Keeps pairs of non-discontinued products with at least
    ``MIN_ORDERS`` orders, ``MIN_CUSTOMERS`` customers and lift > 1.

    Args:
        lines (pd.DataFrame): Order lines from ``load``.
        orders (pd.DataFrame): Orders from ``load``.
        products (pd.DataFrame): Products from ``load``.

    Returns:
        pd.DataFrame: Candidate pairs with product names, prices,
            categories and a ``recommended`` flag; recommended pairs
            first, then by value index.
    """
    table = pair_table(lines, orders, "ProductID")
    a = table.index.get_level_values("a")
    b = table.index.get_level_values("b")
    active = ~products["Discontinued"].reindex(a).to_numpy() & ~products[
        "Discontinued"
    ].reindex(b).to_numpy()

    table = table[
        active
        & (table["orders"] >= MIN_ORDERS)
        & (table["customers"] >= MIN_CUSTOMERS)
        & (table["lift"] > 1)
    ].copy()
    idx_a = table.index.get_level_values("a")
    idx_b = table.index.get_level_values("b")
    table["product_a"] = products["ProductName"].reindex(idx_a).to_numpy()
    table["product_b"] = products["ProductName"].reindex(idx_b).to_numpy()
    table["price_a"] = products["Price"].reindex(idx_a).to_numpy()
    table["price_b"] = products["Price"].reindex(idx_b).to_numpy()
    table["category_a"] = products["CategoryName"].reindex(idx_a).to_numpy()
    table["category_b"] = products["CategoryName"].reindex(idx_b).to_numpy()
    table["recommended"] = table["holds_up"] & table["raises_value"]
    return table.sort_values(["recommended", "value_index"], ascending=False)


def price_check(lines, orders, table):
    """Compare order value with both, only A, or only B of each pick.

    Splits each order's value into the pair's own lines and the rest
    of the order, for every recommended pair.

    Args:
        lines (pd.DataFrame): Order lines from ``load``.
        orders (pd.DataFrame): Orders from ``load``.
        table (pd.DataFrame): Candidates from ``product_candidates``.

    Returns:
        pd.DataFrame: One row per pair and group ("both", "A only",
            "B only") with order count, mean order value, mean pair
            and rest-of-order revenue, median rest, and mean products
            per order.
    """
    baskets = lines.groupby("OrderID")["ProductID"].apply(set)
    rows = []
    for (a, b), pair in table[table["recommended"]].iterrows():
        groups = {
            "both": baskets.map(lambda s: a in s and b in s),
            "A only": baskets.map(lambda s: a in s and b not in s),
            "B only": baskets.map(lambda s: b in s and a not in s),
        }
        for group, mask in groups.items():
            ids = baskets.index[mask]
            sel = lines[lines["OrderID"].isin(ids)]
            in_pair = sel["ProductID"].isin([a, b])
            pair_part = sel[in_pair].groupby("OrderID")["Revenue"].sum().reindex(ids).fillna(0)
            rest = sel[~in_pair].groupby("OrderID")["Revenue"].sum().reindex(ids).fillna(0)
            rows.append({
                "pair": f"{pair['product_a']} (A) + {pair['product_b']} (B)",
                "group": group,
                "orders": len(ids),
                "avg_order": orders.loc[ids, "value"].mean(),
                "avg_A+B_lines": pair_part.mean(),
                "avg_rest": rest.mean(),
                "median_rest": rest.median(),
                "avg_products": orders.loc[ids, "n_products"].mean(),
            })
    return pd.DataFrame(rows)


def short(name, limit=32):
    """Truncate a product name for a chart label.

    Args:
        name (str): Full product name.
        limit (int): Maximum label length in characters.

    Returns:
        str: ``name`` if it fits, else cut and ended with "…" so it
            is at most ``limit`` characters.
    """
    return name if len(name) <= limit else name[: limit - 1].rstrip() + "…"


def plot(table, overall_aov, use_categories):
    """Draw the orders-vs-lift bubble chart and save it.

    Args:
        table (pd.DataFrame): Candidates from ``product_candidates``.
        overall_aov (float): Mean value of all orders, for the chart
            note.
        use_categories (bool): True if no product pair held up; adds
            a note to the title.

    Returns:
        None. Saves the figure to ``CHART``.
    """
    data = table.copy()
    # Pairs share whole-number order counts, so spread them a little sideways at
    # random (fixed seed, so the chart is the same every run).
    rng = np.random.default_rng(0)
    data["x"] = data["orders"] + rng.uniform(-0.18, 0.18, len(data))
    sizes = data["avg_order_value"] / data["avg_order_value"].max() * 900 + 30

    fig, ax = plt.subplots(figsize=(13, 8))
    for key, row in data.iterrows():
        if row["recommended"]:
            color, alpha = COLOR_RECOMMENDED, 0.75
        elif row["holds_up"]:
            color, alpha = COLOR_HOLDS, 0.5
        else:
            color, alpha = COLOR_FADED, 0.25
        ax.scatter(row["x"], row["lift"], s=sizes[key], color=color, alpha=alpha,
                   edgecolor=color, linewidth=1)

    recommended = data[data["recommended"]].sort_values("lift", ascending=False)
    for i, (key, row) in enumerate(recommended.iterrows()):
        label = (
            f"{short(row['product_a'])} + {short(row['product_b'])}\n"
            f"value index {row['value_index']:.2f}, avg order ${row['avg_order_value']:,.0f}"
        )
        ax.annotate(
            label, (row["x"], row["lift"]), xytext=(40, 18 - 30 * (i % 3)),
            textcoords="offset points", fontsize=8,
            arrowprops=dict(arrowstyle="-", color="#777777", lw=0.6),
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=COLOR_RECOMMENDED, lw=0.6),
        )

    # Also label the most frequent pair: bought together most, but low-value orders.
    top_key = data["orders"].idxmax()
    top = data.loc[top_key]
    ax.annotate(
        f"{short(top['product_a'])} + {short(top['product_b'])}\n"
        f"most often together, value index {top['value_index']:.2f}",
        (top["x"], top["lift"]), xytext=(-250, -10), textcoords="offset points",
        fontsize=8, arrowprops=dict(arrowstyle="-", color="#777777", lw=0.6),
        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=COLOR_HOLDS, lw=0.6),
    )

    ax.axhline(1, color="black", lw=0.7, ls="--")
    ax.axvline(MIN_ORDERS - 0.5, color="grey", lw=0.7, ls=":")
    ax.set_xticks(range(MIN_ORDERS, int(data["orders"].max()) + 1))
    ax.set_xlim(MIN_ORDERS - 0.6, data["orders"].max() + 1.6)
    ax.set_ylim(0, data["lift"].max() * 1.12)
    ax.set_xlabel("Orders containing both products")
    ax.set_ylabel("Lift (times more often than chance)")
    title = "Northwind bundle candidates: product pairs bought together"
    if use_categories:
        title += "\n(no product pair held up in both halves; see category table)"
    ax.set_title(title)
    ax.grid(alpha=0.2)

    def handle(color, alpha):
        """Build a marker-only legend handle.

        Args:
            color (str): Marker color.
            alpha (float): Marker opacity.

        Returns:
            matplotlib.lines.Line2D: Legend handle.
        """
        return Line2D([], [], marker="o", ls="", markersize=10, color=color, alpha=alpha)

    ax.legend(
        handles=[handle(COLOR_RECOMMENDED, 0.75), handle(COLOR_HOLDS, 0.5),
                 handle(COLOR_FADED, 0.3)],
        labels=["Recommended: holds up in both halves and raises order value",
                "Holds up in both halves, but orders are not worth more",
                "Does not hold up in both halves"],
        loc="upper right", fontsize=9,
    )
    note = (
        f"Pairs of active products in at least {MIN_ORDERS} orders from at least "
        f"{MIN_CUSTOMERS} customers, with lift > 1. Bubble size = average order value of "
        f"orders containing the pair (all orders: ${overall_aov:,.0f}).\n"
        f"Holds up = lift > 1 and at least {MIN_ORDERS_PER_HALF} orders in each half "
        "(orders split at the median date, Sep 9, 1997). Value index = order value / "
        "average order with the same number of products (median over the pair's orders).\n"
        "Pairs with the same order count are spread slightly sideways."
    )
    fig.text(0.01, 0.01, note, fontsize=8, color="#444444", va="bottom")
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(CHART, dpi=150)
    plt.close(fig)


def main():
    """Run the pair and category analyses and save the chart.

    Args:
        None.

    Returns:
        None. Prints tables to stdout and writes ``CHART``.
    """
    lines, orders, products = load()
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)

    print(f"Orders: {len(orders)}, average order value ${orders['value'].mean():,.0f}")
    print(f"Halves split at {orders['date'].median():%Y-%m-%d}: "
          f"{orders['half'].value_counts().to_dict()}\n")

    table = product_candidates(lines, orders, products)
    cols = ["product_a", "product_b", "price_a", "price_b", "orders", "customers",
            "lift", "orders_first", "lift_first", "orders_second", "lift_second",
            "avg_order_value", "value_index", "holds_up", "recommended"]
    print(f"=== Product pair candidates ({len(table)}) ===")
    print(table[cols].round(2).to_string(index=False))
    print(f"\nHold up in both halves: {int(table['holds_up'].sum())}")
    print(f"Hold up and raise order value (recommended): {int(table['recommended'].sum())}")

    categories = pair_table(lines, orders, "CategoryName").sort_values("lift", ascending=False)
    cat_cols = ["orders", "customers", "lift", "lift_first", "lift_second",
                "avg_order_value", "value_index", "holds_up"]
    print("\n=== Category pairs ===")
    print(categories[cat_cols].round(2).to_string())

    use_categories = not table["holds_up"].any()
    if use_categories:
        print("\nNo product pair holds up in both halves -> use category-level bundles.")
        print(categories[categories["holds_up"] & categories["raises_value"]][cat_cols]
              .round(2).to_string())
    else:
        print(
            "\nProduct pairs hold up, so they are the main recommendation. Category pairs "
            f"are not used: {int((categories['lift'] > 1).sum())} of {len(categories)} have "
            "lift > 1, so categories are not bought together more often than chance."
        )
        print("\n=== Recommended bundles ===")
        print(table[table["recommended"]][cols].round(2).to_string(index=False))
        print("\n=== Price check: both vs only A vs only B (rest = order minus the two products) ===")
        check = price_check(lines, orders, table)
        money = ["avg_order", "avg_A+B_lines", "avg_rest", "median_rest"]
        check[money] = check[money].round(0)
        print(check.round({"avg_products": 1}).to_string(index=False))

    plot(table, orders["value"].mean(), use_categories)
    print(f"\nChart saved to {CHART}")


if __name__ == "__main__":
    main()
