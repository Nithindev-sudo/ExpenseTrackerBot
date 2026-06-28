from db import ExpenseDB

db = ExpenseDB()
rows = db.all_rows()
if rows:
    for i, row in enumerate(rows[-3:], start=len(rows)-2):
        print(f"Row {i}: Note={row['note']}, Amount={row['amount']} (type: {type(row['amount']).__name__}), Category={row['category']}")
else:
    print('No expenses in database')
