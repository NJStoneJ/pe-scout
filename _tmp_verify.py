import sys, os
sys.path.insert(0, ".")
from backend.agents.pe_agent import PEAgent

ag = PEAgent()
txt = ag._tax_reply({}, "test")
out = []
out.append("==== _tax_reply output ====")
out.append(txt)
ok = ("596,500" in txt) and ("96,500" in txt) and ("境外抵免 500,000 = 补缴 0" in txt)
out.append("AGENT ALIGNED WITH CALCULATOR: " + str(ok))
with open("_tmp_out.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
# self cleanup
try:
    os.remove("_tmp_verify.py")
except Exception:
    pass
