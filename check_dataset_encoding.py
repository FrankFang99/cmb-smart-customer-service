import json
with open('data/evaluation_dataset_v5.1.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 检查特定样本的原始数据
print("Sample 8 (cons_prod_credit):")
s = data['samples'][7]
print(f"  question bytes: {s['question'].encode('utf-8')}")
print(f"  question repr: {repr(s['question'])}")

print("\nSample 9 (sales_loan_prod):")
s = data['samples'][8]
print(f"  question repr: {repr(s['question'])}")

print("\nAll sales_loan_prod samples:")
for i, s in enumerate(data['samples']):
    if s['intent'] == 'sales_loan_prod':
        print(f"  {i}: {repr(s['question'])}")