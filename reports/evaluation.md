# Evaluation

## Development set (139 clauses)

Model scored with 5-fold stratified cross-validation. Rules were tuned on this set, so their dev numbers are optimistic. Risk labels: {'NEUTRAL': 46, 'RISKY': 56, 'TENANT_FAVORABLE': 37}

| System | Type accuracy | Type macro-F1 | Risk accuracy | Risk macro-F1 | RISKY precision | RISKY recall |
|---|---|---|---|---|---|---|
| Rule baseline | 0.76 | 0.76 | 0.92 | 0.92 | 0.98 | 0.91 |
| Trained model (TF-IDF + LR) | 0.59 | 0.58 | 0.41 | 0.38 | 0.47 | 0.57 |
| Hybrid (rules + model) | 0.78 | 0.78 | 0.74 | 0.71 | 0.69 | 0.98 |

## Rule baseline: risk per class

| Label | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| RISKY | 0.98 | 0.91 | 0.94 | 56 |
| NEUTRAL | 0.85 | 0.96 | 0.90 | 46 |
| TENANT_FAVORABLE | 0.94 | 0.89 | 0.92 | 37 |

Confusion matrix (rows = true, cols = predicted: RISKY, NEUTRAL, TENANT_FAVORABLE)

```
  51     5     0
   0    44     2
   1     3    33
```

## Trained model (TF-IDF + LR): risk per class

| Label | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| RISKY | 0.47 | 0.57 | 0.52 | 56 |
| NEUTRAL | 0.36 | 0.37 | 0.37 | 46 |
| TENANT_FAVORABLE | 0.33 | 0.22 | 0.26 | 37 |

Confusion matrix (rows = true, cols = predicted: RISKY, NEUTRAL, TENANT_FAVORABLE)

```
  32    17     7
  20    17     9
  16    13     8
```

## Hybrid (rules + model): risk per class

| Label | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| RISKY | 0.69 | 0.98 | 0.81 | 56 |
| NEUTRAL | 1.00 | 0.37 | 0.54 | 46 |
| TENANT_FAVORABLE | 0.74 | 0.84 | 0.78 | 37 |

Confusion matrix (rows = true, cols = predicted: RISKY, NEUTRAL, TENANT_FAVORABLE)

```
  55     0     1
  19    17    10
   6     0    31
```

## Where the rule baseline disagrees with the labels

Use these to write new rules or fix labels (dev set only).

| id | true | rules | clause |
|---|---|---|---|
| c007 | TENANT_FAVORABLE | RISKY | The rent shall remain fixed for the entire term of this agreement and shall not be revised during the term. |
| c019 | RISKY | NEUTRAL | The deposit shall be returned to the Lessee only after the Lessor finds a new tenant for the premises. |
| c027 | NEUTRAL | TENANT_FAVORABLE | The deposit shall be refunded subject to deduction of unpaid rent, unpaid utility bills and the cost of repairing damage beyond normal wear and tear. |
| c029 | RISKY | NEUTRAL | Upon handing over of keys, the deposit will be returned, less any deductions the Owner deems necessary. |
| c069 | RISKY | NEUTRAL | The Tenant shall get the entire flat repainted at his own cost before vacating, regardless of its condition. |
| c074 | RISKY | NEUTRAL | If any appliance supplied by the Owner breaks down, the Tenant shall replace it with a new one at his cost. |
| c083 | TENANT_FAVORABLE | NEUTRAL | No late fee shall be charged for payments received within five days of the due date. |
| c095 | NEUTRAL | TENANT_FAVORABLE | During the last month of tenancy, the Tenant shall allow prospective tenants to view the premises at reasonable hours with prior intimation. |
| c100 | RISKY | NEUTRAL | The Lessor's agents may show the flat to buyers at any hour without informing the Lessee. |
| c122 | TENANT_FAVORABLE | NEUTRAL | The Tenant may install a washing machine, internet connection and other household appliances at his own cost and remove them on vacating. |
| c125 | TENANT_FAVORABLE | NEUTRAL | The Tenant may work from home and receive deliveries at the premises. |

> Caveat: the seed dataset and the rules were written by the same author, so rule-baseline scores are likely optimistic. Re-run on clauses from real agreements labelled by your team before quoting these numbers.