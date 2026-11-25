"""Find overlooked high-potential country markets in Northwind data.

Prints per-country growth tables and saves Question1_markets.png.
"""

# Definitions
# Market     = customer country (Customers.Country).
# Potential  = revenue growth and active-customer growth, comparing the
#              same days in consecutive years. Two comparisons are made:
#                * Jul 4 - Dec 31, 1997 vs 1996 (orders start 1996-07-04)
#                * Jan 1 - May 6, 1998 vs 1997  (orders end 1998-05-06)
# Overlooked = few customers (customer accounts in the Customers table).
# Overlooked high-potential (per comparison) = fewer customers than the
#              median country, revenue growth above the median, and
#              active-customer growth at or above the median (the median
#              is 0%: not losing customers).
# A result is treated as robust only if a country qualifies in both
# comparisons.
#
# Concentration check: the share of a country's revenue increase that
# came from its single biggest-growing customer, so growth driven by one
# account is visible.
# Small-sample flag = 3 or fewer customers. Spain is highlighted
# separately.
#
# Output: tables printed to the console, and Question1_markets.png.

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D

HERE = Path(__file__).resolve().parent
DATA = HERE / "Northwind.xlsx"
CHART = HERE / "Question1_markets.png"
SMALL_SAMPLE_MAX = 3  # countries with this many customers or fewer are flagged
HIGHLIGHT = "Spain"

# (short name, label, previous window, current window), dates inclusive
COMPARISONS = [
    ("H2", "Jul 4 - Dec 31, 1997 vs 1996",
     ("1996-07-04", "1996-12-31"), ("1997-07-04", "1997-12-31")),
    ("Early98", "Jan 1 - May 6, 1998 vs 1997",
     ("1997-01-01", "1997-05-06"), ("1998-01-01", "1998-05-06")),
]

COLOR_QUALIFIES = "#e07a1f"
COLOR_OTHER = "#2a6f97"
COLOR_HIGHLIGHT = "#2e9e5b"


def load():
    """Load Northwind sheets and join order lines to customers.

    Args:
        None.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: ``lines``, one row per order
            line with OrderDate, CustomerID, CompanyName, Country and
            Revenue; and ``customers``, with CustomerID, CompanyName
            and Country.
    """
    sheets = pd.read_excel(DATA, sheet_name=["Orders", "Orders Details", "Customers"])
    orders = sheets["Orders"][["OrderID", "CustomerID", "OrderDate"]]
    details = sheets["Orders Details"]
    customers = sheets["Customers"][["CustomerID", "CompanyName", "Country"]]

    details = details.assign(
        Revenue=details["UnitPrice"] * details["Quantity"] * (1 - details["Discount"])
    )
    lines = details.merge(orders, on="OrderID", how="left").merge(
        customers, on="CustomerID", how="left"
    )
    assert lines["OrderDate"].notna().all(), "order lines without a matching order"
    assert lines["Country"].notna().all(), "orders without a matching customer"
    return lines, customers


def in_window(lines, window):
    """Return order lines dated inside a window.

    Args:
        lines (pd.DataFrame): Order lines with an OrderDate column.
        window (tuple[str, str]): Start and end dates, both inclusive.

    Returns:
        pd.DataFrame: Rows of ``lines`` inside the window.
    """
    start, end = pd.Timestamp(window[0]), pd.Timestamp(window[1])
    return lines[(lines["OrderDate"] >= start) & (lines["OrderDate"] <= end)]


def pct_change(new, old):
    """Return the percent change from old to new.

    Args:
        new (pd.Series): Values in the later window.
        old (pd.Series): Values in the earlier window.

    Returns:
        pd.Series: Percent change; NaN where ``old`` is 0.
    """
    return (new - old) / old.where(old != 0) * 100


def build_table(lines, customers, prev_window, cur_window):
    """Build the per-country table for one year-over-year comparison.

    Args:
        lines (pd.DataFrame): Joined order lines from ``load``.
        customers (pd.DataFrame): Customers with CustomerID and Country.
        prev_window (tuple[str, str]): Earlier window's start and end.
        cur_window (tuple[str, str]): Later window's start and end.

    Returns:
        pd.DataFrame: One row per country, sorted by revenue growth,
            with customer counts, revenue and active customers per
            window, growth percentages, the top customer's share of
            the increase (NaN if revenue did not rise), and
            small-sample and overlooked flags.
    """
    prev = in_window(lines, prev_window)
    cur = in_window(lines, cur_window)

    table = pd.DataFrame(
        {
            "customers": customers.groupby("Country")["CustomerID"].nunique(),
            "total_revenue": lines.groupby("Country")["Revenue"].sum(),
            "rev_prev": prev.groupby("Country")["Revenue"].sum(),
            "rev_cur": cur.groupby("Country")["Revenue"].sum(),
            "active_prev": prev.groupby("Country")["CustomerID"].nunique(),
            "active_cur": cur.groupby("Country")["CustomerID"].nunique(),
        }
    ).fillna(0)

    table["revenue_growth_pct"] = pct_change(table["rev_cur"], table["rev_prev"])
    table["customer_growth_pct"] = pct_change(table["active_cur"], table["active_prev"])
    table["small_sample"] = table["customers"] <= SMALL_SAMPLE_MAX

    # Concentration: share of the country's revenue increase that came from the
    # single customer whose revenue rose the most. Only meaningful when revenue
    # went up; values over 100% mean other customers shrank.
    per_customer = cur.groupby(["Country", "CustomerID"])["Revenue"].sum().sub(
        prev.groupby(["Country", "CustomerID"])["Revenue"].sum(), fill_value=0
    )
    increase = table["rev_cur"] - table["rev_prev"]
    top_gain = per_customer.groupby("Country").max().reindex(table.index)
    table["top_customer_share_pct"] = (top_gain / increase.where(increase > 0)) * 100

    med = table[["customers", "revenue_growth_pct", "customer_growth_pct"]].median()
    table["overlooked_high_potential"] = (
        (table["customers"] < med["customers"])
        & (table["revenue_growth_pct"] > med["revenue_growth_pct"])
        & (table["customer_growth_pct"] >= med["customer_growth_pct"])
    )
    return table.sort_values("revenue_growth_pct", ascending=False)


def customer_breakdown(lines, country):
    """Tabulate revenue and orders per customer of one country.

    Args:
        lines (pd.DataFrame): Joined order lines from ``load``.
        country (str): Country name as in Customers.Country.

    Returns:
        pd.DataFrame: One row per company; for each window in
            ``COMPARISONS``, revenue and order-count columns (0 if
            none).
    """
    parts = {}
    for _, _, prev_w, cur_w in COMPARISONS:
        for window in (prev_w, cur_w):
            sel = in_window(lines[lines["Country"] == country], window)
            key = f"{window[0][:7]}..{window[1][5:7]}"
            parts[(key, "revenue")] = sel.groupby("CompanyName")["Revenue"].sum()
            parts[(key, "orders")] = sel.groupby("CompanyName")["OrderID"].nunique()
    return pd.DataFrame(parts).fillna(0)


def jitter_x(table):
    """Offset x positions of countries that share a customer count.

    Args:
        table (pd.DataFrame): Country table with ``customers`` and
            ``revenue_growth_pct`` columns.

    Returns:
        pd.Series: Customer count plus a sideways offset, 0.13 apart
            and ordered by growth within each count.
    """
    x = table["customers"].astype(float)
    for _, group in table.groupby("customers"):
        if len(group) > 1:
            order = group["revenue_growth_pct"].sort_values().index
            for i, country in enumerate(order):
                x[country] += (i - (len(order) - 1) / 2) * 0.13
    return x


def draw_panel(ax, table, title, robust, size_scale):
    """Draw one customers-vs-revenue-growth bubble chart.

    Args:
        ax (matplotlib.axes.Axes): Axes to draw on.
        table (pd.DataFrame): Country table from ``build_table``.
        title (str): Panel title, the comparison label.
        robust (set[str]): Countries qualifying in both comparisons.
        size_scale (float): Total revenue drawn at the largest bubble
            size, shared by both panels.

    Returns:
        list[str]: Countries left out because they had no revenue in
            the earlier window.
    """
    data = table.dropna(subset=["revenue_growth_pct"]).copy()
    data["x"] = jitter_x(data)
    sizes = data["total_revenue"] / size_scale * 1600 + 40

    for country, row in data.iterrows():
        if country == HIGHLIGHT:
            color = COLOR_HIGHLIGHT
        elif row["overlooked_high_potential"]:
            color = COLOR_QUALIFIES
        else:
            color = COLOR_OTHER
        small = row["small_sample"]
        ax.scatter(
            row["x"], row["revenue_growth_pct"], s=sizes[country],
            facecolor=color, edgecolor=color, alpha=0.25 if small else 0.6,
            linestyle="--" if small else "-", linewidth=1.4,
        )

        text = country
        if country in robust:
            text += " (both periods)"
        if country == HIGHLIGHT:
            share = row["top_customer_share_pct"]
            text += (
                f"\n{row['active_prev']:.0f} -> {row['active_cur']:.0f} active customers"
                + (f"; top customer = {share:.0f}% of increase" if pd.notna(share) else "")
            )
        emphasis = row["overlooked_high_potential"] or country == HIGHLIGHT
        # Crowded 2-customer cluster: labels left of the bubble, plus a few nudges.
        left = (row["customers"] == 2 and row["x"] < 2) or country == "Belgium"
        offset = (-9, 3) if left else (7, 3)
        if country == "Portugal":
            offset = (-9, -10)
        ax.annotate(
            text, (row["x"], row["revenue_growth_pct"]),
            xytext=offset, textcoords="offset points",
            ha="right" if left else "left", fontsize=8.5,
            fontweight="bold" if emphasis else "normal",
            color=COLOR_HIGHLIGHT if country == HIGHLIGHT else "black",
        )

    # Linear between -100% and +100%, logarithmic beyond, so a few very large
    # growth rates don't flatten everyone else.
    ax.set_yscale("symlog", linthresh=100)
    ticks = [-100, -50, 0, 50, 100, 200, 500, 1000, 2000]
    ax.set_yticks(ticks)
    ax.set_yticklabels([f"{t:+d}%" if t else "0%" for t in ticks])
    ax.set_ylim(-110, 4000)
    ax.set_xticks(range(0, int(table["customers"].max()) + 2))

    ax.axhline(data["revenue_growth_pct"].median(), color="grey", lw=0.8, ls=":")
    ax.axvline(table["customers"].median(), color="grey", lw=0.8, ls=":")
    ax.axhline(0, color="black", lw=0.6)
    ax.set_title(title, fontsize=11)
    ax.set_xlabel("Number of customers")
    ax.grid(alpha=0.2)
    return table.index[table["revenue_growth_pct"].isna()].tolist()


def plot(tables, robust):
    """Draw both comparisons side by side and save the chart.

    Args:
        tables (dict[str, pd.DataFrame]): Country table for each
            comparison short name in ``COMPARISONS``.
        robust (set[str]): Countries qualifying in both comparisons.

    Returns:
        None. Saves the figure to ``CHART``.
    """
    fig, axes = plt.subplots(1, 2, figsize=(17, 8), sharey=True)
    size_scale = max(t["total_revenue"].max() for t in tables.values())
    missing_notes = []
    for ax, (key, label, prev_w, _) in zip(axes, COMPARISONS):
        missing = draw_panel(ax, tables[key], label, robust, size_scale)
        if missing:
            missing_notes.append(
                f"{label}: not plotted (no sales in the earlier window): {', '.join(missing)}"
            )
    axes[0].set_ylabel("Revenue growth (%), same days year over year")

    def handle(color, alpha=0.7, face=True):
        """Build a marker-only legend handle.

        Args:
            color (str): Marker color.
            alpha (float): Marker opacity.
            face (bool): Fill the marker if True, else outline only.

        Returns:
            matplotlib.lines.Line2D: Legend handle.
        """
        return Line2D([], [], marker="o", ls="", markersize=11, alpha=alpha,
                      markerfacecolor=color if face else "none", markeredgecolor=color)

    axes[0].legend(
        handles=[handle(COLOR_QUALIFIES), handle(COLOR_OTHER), handle(COLOR_HIGHLIGHT),
                 handle("grey", 1, face=False)],
        labels=["Overlooked high-potential in this period", "Other markets",
                f"{HIGHLIGHT} (highlighted)",
                f"Faded, dashed = small sample ({SMALL_SAMPLE_MAX} or fewer customers)"],
        loc="lower right", fontsize=9,
    )

    robust_text = ", ".join(sorted(robust)) if robust else "none"
    fig.suptitle(
        "Northwind markets: customer base vs revenue growth, two comparisons\n"
        f"Qualifies in both periods: {robust_text}",
        fontsize=13,
    )
    note = (
        "Bubble size = total revenue (all orders, Jul 1996 - May 1998), same scale in both panels. "
        "Dotted lines = medians. Countries with the same customer count are spread slightly sideways.\n"
        "Overlooked high-potential = below-median customers, above-median revenue growth, and "
        "active customers not shrinking (median customer growth = 0%). "
        "Y-axis is linear from -100% to +100%, logarithmic above."
    )
    if missing_notes:
        note += "\n" + "\n".join(missing_notes)
    fig.text(0.01, 0.01, note, fontsize=8, color="#444444", va="bottom")
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(CHART, dpi=150)
    plt.close(fig)


def main():
    """Run both comparisons, print the results, and save the chart.

    Args:
        None.

    Returns:
        None. Prints tables to stdout and writes ``CHART``.
    """
    lines, customers = load()
    tables = {
        key: build_table(lines, customers, prev_w, cur_w)
        for key, _, prev_w, cur_w in COMPARISONS
    }

    cols = [
        "customers", "small_sample", "rev_prev", "rev_cur", "revenue_growth_pct",
        "active_prev", "active_cur", "customer_growth_pct", "top_customer_share_pct",
        "overlooked_high_potential",
    ]
    pd.set_option("display.width", 220)
    qualified = {}
    for key, label, _, _ in COMPARISONS:
        table = tables[key]
        qualified[key] = set(table.index[table["overlooked_high_potential"]])
        print(f"=== {label} ===")
        print(table[cols].round(1).to_string())
        print(f"Overlooked high-potential: {', '.join(sorted(qualified[key])) or 'none'}\n")

    robust = set.intersection(*qualified.values())
    print("=== Robustness check ===")
    for key, label, _, _ in COMPARISONS:
        print(f"{label}: {', '.join(sorted(qualified[key])) or 'none'}")
    print(f"Qualifies in both: {', '.join(sorted(robust)) or 'none'}\n")

    for country in sorted(robust | {HIGHLIGHT}):
        print(f"=== {country}: revenue and orders per customer ===")
        print(customer_breakdown(lines, country).round(0).to_string(), "\n")

    plot(tables, robust)
    print(f"Chart saved to {CHART}")


if __name__ == "__main__":
    main()
