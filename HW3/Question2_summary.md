# Question 2: Product Bundles to Increase Order Value

## Question
Which products should Northwind bundle to increase order value?

## Why it matters
A bundle that gets customers to add a second product makes each order bigger without needing new customers. But if a pair only looks valuable because its products are expensive, a bundle would just discount sales that would have happened anyway.

## Approach
I looked for pairs of active products that customers buy together more often than chance, in at least 4 orders from at least 2 customers, and kept only pairs that held up in both halves of the data and appeared in orders worth more than similar-sized orders. For the pairs that passed, I compared orders with both products against orders with only one of them, to see where the extra value comes from (code: `Question2_bundles.py`, chart: `Question2_bundles.png`).

## Main finding
- **Buying the two products together adds the second product's value, but nothing more.** In orders with both products, the rest of the order is no bigger than in orders with only one of them: its median is the same or lower for all three pairs.
- **Three pairs pass every test, and all three include a premium cheese:**

  | Bundle | Orders together | Avg order (both) | Avg order (A only / B only) |
  |---|---|---|---|
  | Uncle Bob's Organic Dried Pears + Mozzarella di Giovanni | 4 | $2,922 | $1,930 / $1,893 |
  | Pavlova + Camembert Pierrot | 6 | $3,584 | $1,511 / $2,265 |
  | Camembert Pierrot + Fløtemysost | 6 | $2,930 | $2,352 / $1,671 |

- **The higher value comes from the products' own lines.** For Pears + Mozzarella, the two products are worth $1,524 when bought together, about the same as when bought separately ($734 + $662). The other two pairs show somewhat larger spend on the pair when bought together, but this rests on only 6 orders each.
- **Category bundles have no signal.** None of the 28 category pairs is bought together more often than chance.
- **The most frequent pair is a poor bundle.** Sir Rodney's Scones + Sirop d'érable are bought together most often (8 orders), but in low-value orders, so bundling them would not raise order value.

## Business implication
- **Use these bundles as cross-sells, not as a way to grow the whole order.** The realistic gain is getting customers who buy one product to add the other, which adds roughly $400–900 to that order.
- **Start with Pavlova + Camembert Pierrot and Dried Pears + Mozzarella di Giovanni.** Offer the cheese as a suggested add-on to customers buying the other product, with little or no discount, because customers who buy both already pay full value for them.
- **Drop Camembert Pierrot + Fløtemysost.** Its orders are only about average for their size, and the rest of those orders is smaller than when either product is bought alone.
- **Test before rolling out.** With only 4–6 orders behind each pair, run the offer for a limited period and compare order values with customers who were not offered it.
