"""Debug which rule matches"""
import re

text = "你好"
text_lower = text.lower()

# All rule groups
all_rules = [
    ("P0", [
        (r"(杀|死|暴|炸).*(你|我|银|行|卡)|诈骗|被骗|小偷", "p0_security"),
    ]),
    ("ACCOUNT", [
        (r"余额多少|还剩多少钱|账户余额|卡里还有", "info_acc_balance"),
        (r"交易记录|消费明细|消费记录|交易流水|近期.*消费", "info_tran_record"),
    ]),
    ("BILL", [
        (r"(欠|还欠|还欠着).*?(多少|钱|款|账单)", "info_bill_amount"),
        (r"账单(多少|金额)?|本期账单|欠了", "info_bill_amount"),
    ]),
    ("SYSTEM", [
        (r"^(你好|您好|hi|hello|hi~|hey)", "sys_greeting"),
        (r"请问|咨询|问一下", "sys_greeting"),
    ]),
    ("INVALID", [
        (r"^(嗯|哦|啊|呃|咦|哈)$", "sys_invalid"),
    ]),
]

print(f"Text: '{text}'")
print()

for group_name, rules in all_rules:
    for pattern, intent_str in rules:
        result = re.search(pattern, text_lower)
        if result:
            print(f"MATCH [{group_name}]: pattern='{pattern}' -> {intent_str}")
            break