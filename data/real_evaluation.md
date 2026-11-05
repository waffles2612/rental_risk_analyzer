# Evaluation on labelled real agreements

1108 labelled clauses from 46 agreements (35 Indian, 11 foreign); 5-fold cross-validation grouped by agreement. Labels: {'NEUTRAL': 962, 'TENANT_FAVORABLE': 23, 'RISKY': 123}. Extra training data: 199 authored + 81 synthetic clauses.

## All agreements (1108 clauses, 123 risky)

| System | Acc. | Macro-F1 | Risky P | Risky R | Risky F1 | Fav. F1 | Risky-vs-rest F1 |
|---|---|---|---|---|---|---|---|
| Rules | 0.85 | 0.48 | 0.55 | 0.32 | 0.40 | 0.12 | 0.40 |
| Classifier, authored data only | 0.32 | 0.25 | 0.16 | 0.76 | 0.26 | 0.10 | 0.26 |
| Classifier, real + authored (grouped CV) | 0.85 | 0.56 | 0.41 | 0.39 | 0.40 | 0.36 | 0.40 |
| Hybrid: rules + real-trained classifier | 0.83 | 0.55 | 0.44 | 0.55 | 0.49 | 0.27 | 0.49 |

## Indian agreements only (648 clauses, 47 risky)

| System | Acc. | Macro-F1 | Risky P | Risky R | Risky F1 | Fav. F1 | Risky-vs-rest F1 |
|---|---|---|---|---|---|---|---|
| Rules | 0.86 | 0.46 | 0.47 | 0.32 | 0.38 | 0.09 | 0.38 |
| Classifier, authored data only | 0.34 | 0.25 | 0.11 | 0.81 | 0.19 | 0.09 | 0.19 |
| Classifier, real + authored (grouped CV) | 0.89 | 0.61 | 0.33 | 0.38 | 0.35 | 0.52 | 0.35 |
| Hybrid: rules + real-trained classifier | 0.85 | 0.54 | 0.37 | 0.55 | 0.44 | 0.25 | 0.44 |

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