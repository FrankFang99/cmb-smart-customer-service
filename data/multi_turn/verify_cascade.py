import sys
sys.path.insert(0, r'D:\Learning\AI\面试\AI智能客服')
from src.agent.e2e_pipeline import create_e2e_pipeline
p = create_e2e_pipeline()
for q in ['你好', '查询账户余额', '信用卡激活', '我刚被骗了', '我信用卡被盗刷了 5000 块', '95555 客服电话']:
    r = p.handle(q, session_id='s1')
    cascade = r.get('cascade', '?')
    llm_called = r.get('llm_called', None)
    action = r['action']
    elapsed = r['elapsed_ms']
    print(f'{q}: cascade={cascade} llm={llm_called} action={action} {elapsed}ms')
