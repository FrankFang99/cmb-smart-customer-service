from src.agent.customer_service_agent import CustomerServiceAgent
from src.config import settings

agent = CustomerServiceAgent(settings)

test_questions = [
    '我卡里还有多少钱',
    '信用卡欠了20万还不上了',
    '卡丢了怎么办',
    '转账要手续费吗'
]

for q in test_questions:
    result = agent.chat(q)
    print('Q:', q)
    print('  Intent:', result['intent'])
    print('  Answer:', result['answer'][:80], '...')
    print()