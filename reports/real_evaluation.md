# Evaluation on labelled real agreements

1108 labelled clauses from 46 agreements (35 Indian, 11 foreign); 5-fold cross-validation grouped by agreement. Labels: {'NEUTRAL': 962, 'TENANT_FAVORABLE': 23, 'RISKY': 123}. Extra training data: 199 authored + 81 synthetic clauses.

## All agreements (1108 clauses, 123 risky)

| System | Acc. | Macro-F1 | Risky P | Risky R | Risky F1 | Fav. F1 | Risky-vs-rest F1 |
|---|---|---|---|---|---|---|---|
| Rules | 0.86 | 0.50 | 0.70 | 0.34 | 0.46 | 0.12 | 0.46 |
| Classifier, authored data only | 0.32 | 0.25 | 0.16 | 0.76 | 0.26 | 0.10 | 0.26 |
| Classifier, real + authored (grouped CV) | 0.86 | 0.56 | 0.44 | 0.39 | 0.41 | 0.35 | 0.41 |
| Hybrid: rules + real-trained classifier | 0.85 | 0.57 | 0.51 | 0.59 | 0.55 | 0.24 | 0.55 |

## Indian agreements only (648 clauses, 47 risky)

| System | Acc. | Macro-F1 | Risky P | Risky R | Risky F1 | Fav. F1 | Risky-vs-rest F1 |
|---|---|---|---|---|---|---|---|
| Rules | 0.88 | 0.47 | 0.72 | 0.28 | 0.40 | 0.09 | 0.40 |
| Classifier, authored data only | 0.34 | 0.25 | 0.11 | 0.81 | 0.19 | 0.09 | 0.19 |
| Classifier, real + authored (grouped CV) | 0.89 | 0.60 | 0.36 | 0.40 | 0.38 | 0.48 | 0.38 |
| Hybrid: rules + real-trained classifier | 0.86 | 0.54 | 0.43 | 0.55 | 0.49 | 0.21 | 0.49 |

Foreign agreements (tagged automatically; check this list):

- 175488575-House-Rental-Agreement.pdf.docx
- 249104436-House-Rental-Agreement.pdf.docx
- 267005869-Rental-Tenant.pdf.docx
- 294331674-Rental-Agreement.pdf.docx
- 323828497-Rental-Agreement-Micky.pdf.docx
- 334060786-House-Rental-Agreement.pdf.docx
- 46239065-Standard-Rental-Agreement-Rental-With-Performance-Fee.pdf.docx
- 63057680-Rental-Agreement.pdf.docx
- 6683127-House-Rental-Contract-GERALDINE-GALINATO-v2-Page-1.pdf.docx
- 6683129-House-Rental-Contract-Geraldine-Galinato-v2.pdf.docx
- 81655723-Rental-Agreement.pdf.docx