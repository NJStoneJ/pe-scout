"""自由文本PE风险要素提取器 — 基于关键词规则匹配"""

import re


# 15道题对应的关键词模式
QUESTION_PATTERNS = [
    # (qid, positive_patterns, negative_patterns)
    (1, [
        r'固定营业场所|营业场所|办公室|工厂|仓库|车间|门店|展示厅|经营场所|办公场所|租了|租赁|设有|设立',
        r'租了.*办公室|租了.*仓库|设有.*办公室|设有.*办事处|派驻|驻.*德国|德国.*办公',
    ], [
        r'无固定营业场所|没有.*场所|纯线上|无实体|跨境.*电商.*直邮|不设.*办公室',
    ]),
    (2, [
        r'自有|长期租赁|长期租|长期.*合同|3年.*租|5年.*租|自有.*房产|购买.*办公室|买了.*办公',
        r'租约.*\d+年|合同.*期限.*\d+年',
    ], [
        r'临时|短期|借用|共享办公.*按天|临时.*展位|展会.*临时|酒店.*办公|居家.*办公',
    ]),
    (3, [
        r'超过.*6.*月|超过.*半年|半年以上|\d+年.*运营|已运营.*\d+.*月|已.*\d+.*年|长期.*存在|持续.*\d+.*月',
        r'持续.*超过|已运营.*\d+个月|运营了.*\d+年',
    ], [
        r'不足.*6.*月|不足半年|短期.*项目|临时|刚.*设立|刚开始|新.*设立|3.*月.*以内',
    ]),
    (4, [
        r'存储.*货物|仓储|仓库.*发货|发货|交付.*货物|展示.*商品|陈列|库存|物流.*中心|配送|分拣|打包',
    ], [
        r'不.*仅.*存储|不.*仅.*仓库|还.*销售|还.*零售|还.*展示.*销售|现场.*销售',
    ]),
    (5, [
        r'采购.*货物|采购.*商品|采购.*信息|收集信息|采购.*办公|市场.*调研|市场.*信息',
    ], [
        r'不.*仅.*采购|还.*销售|还.*服务|核心.*业务',
    ]),
    (6, [
        r'准备性|辅助性|辅助.*活动|市场.*调研|广告.*宣传|客户.*关系.*维护|不.*直接.*产生.*收入|联络|信息.*收集|售后服务',
    ], [
        r'核心.*业务|直接.*销售|直接.*产生.*收入|合同.*签订|谈判.*签约',
    ]),
    (7, [
        r'多处.*场所|多个.*办公|多个.*仓库|拆分|分散.*多个|反碎片|组合.*整体|各.*场所.*组合',
    ], []),
    (8, [
        r'建筑工地|建造|装配|安装.*工程|施工|工程.*项目|建设|安装.*设备|监理|光伏.*安装|电站.*安装|铺设|管道.*安装',
    ], [
        r'没有.*工程|无.*建筑|无.*安装|不.*涉及.*工程',
    ]),
    (9, [
        r'超过.*12.*月|超过.*一年|12.*月.*以上|一年.*以上|\d+年.*工期|工期.*\d+年|工期.*\d+.*月',
        r'持续.*\d+.*月.*工程|施工.*\d+.*月',
    ], [
        r'不足.*12.*月|不足一年|少于.*12|工期.*\d+.*月.*以下|3.*月.*完工|6.*月.*完工',
    ]),
    (10, [
        r'多个.*合同|关联.*合同|拆分.*合同|同一.*项目.*合同|多个.*阶段|分批.*合同|人为.*拆分',
    ], []),
    (11, [
        r'派驻.*人员|派驻.*员工|雇员|人员.*德国|德国.*人员|代表.*德国|德国.*代表|销售.*人员|当地.*员工|当地.*雇佣|工程师.*驻|派遣|常驻|当地.*律师',
    ], [
        r'没有.*派驻|无.*人员.*德国|无.*当地.*员工|纯.*远程|不.*派驻',
    ]),
    (12, [
        r'以.*企业.*名义.*签订.*合同|以.*公司.*名义.*签|有权.*签.*合同|签订.*合同.*权|签约.*权|代表.*签.*合同|经常.*签订|经常.*签.*合同|签署.*合同|缔约',
        r'经常.*以.*名义|授权.*签',
    ], [
        r'无权.*签.*合同|不.*签.*合同|合同.*由.*总部.*签|总部.*签.*合同|无权.*缔约|不.*代表.*签',
    ]),
    (13, [
        r'独立.*代理|独立.*代表|代理.*多家|多家.*代理|自负.*盈亏|独立.*经营|佣金.*代理|经纪人|独立.*第三方',
    ], [
        r'非独立|不.*独立|专属.*代理|独家.*代理|只.*代理.*一家|仅.*代理.*一家|全部.*为.*该.*企业',
    ]),
    (14, [
        r'全部.*为.*该.*企业|仅.*为.*该.*企业|只.*为.*一家|几乎.*全部.*为.*该|90%|绝大部分.*业务.*该|主要.*服务.*该.*企业',
    ], []),
    (15, [
        r'代理人.*有.*办公室|代理人.*办公.*场所|德国.*办公室.*代理|设有.*办公.*代理|固定.*办公.*代理',
        r'办公.*室.*为.*代理',
    ], []),
]


def extract_answers(text: str) -> dict:
    """从自由文本中提取15道题的答案。返回 {qid: bool, ...}"""
    answers = {}

    for qid, pos_patterns, neg_patterns in QUESTION_PATTERNS:
        pos_score = 0
        neg_score = 0

        for pat in pos_patterns:
            if re.search(pat, text):
                pos_score += 1

        for pat in neg_patterns:
            if re.search(pat, text):
                neg_score += 1

        if pos_score > neg_score:
            answers[qid] = True
        elif neg_score > pos_score:
            answers[qid] = False
        # If equal (both 0 or tie), leave unanswered (user can manually adjust)

    return answers


def extract_profile(text: str) -> dict:
    """提取企业基本画像信息"""
    profile = {}

    # 行业
    industry_patterns = [
        (r'电商|跨境.*零售|亚马逊|独立站|线上.*销售|网店', '跨境电商/零售'),
        (r'光伏|新能源|太阳能|风电|锂电|储能|电池', '新能源'),
        (r'律所|律师|法律服务|法律.*咨询|知识产权', '专业服务/法律'),
        (r'软件|IT|信息.*技术|开发.*外包|SAP|系统.*开发|程序员|码农', 'IT外包/信息技术'),
        (r'制造|工厂|生产|机械|汽车.*零件|零部件', '制造业'),
        (r'咨询|顾问|管理.*咨询|战略.*咨询', '咨询服务业'),
    ]
    for pat, industry in industry_patterns:
        if re.search(pat, text):
            profile['industry'] = industry
            break

    # 提取收入
    revenue_match = re.search(r'(?:收入|营收|销售额|合同.*金额|合同.*额).*?[约]?\s*[€欧]?\s*(\d[\d,.]*)\s*万', text)
    if revenue_match:
        profile['revenue_hint'] = revenue_match.group(0)

    # 提取员工数
    emp_match = re.search(r'(\d+)\s*[名个位人]\s*(?:员工|雇员|人员|工程师|律师|技工)', text)
    if emp_match:
        profile['employees_hint'] = int(emp_match.group(1))

    # 提取德国城市
    city_patterns = [
        (r'柏林', 'Berlin'), (r'慕尼黑', 'München'), (r'法兰克福', 'Frankfurt'),
        (r'汉堡', 'Hamburg'), (r'杜塞尔多夫', 'Düsseldorf'), (r'斯图加特', 'Stuttgart'),
        (r'科隆', 'Köln'), (r'纽伦堡', 'Nürnberg'), (r'莱比锡', 'Leipzig'),
        (r'巴伐利亚', 'Bayern'), (r'北威州|北威', 'NRW'),
    ]
    for pat, city in city_patterns:
        if re.search(pat, text):
            profile['location_hint'] = city
            break

    return profile


def get_extraction_summary(answers: dict, profile: dict) -> str:
    """生成提取摘要，告知用户哪些题被自动识别了"""
    filled = len(answers)
    total = 15
    lines = [f"从文本中自动识别了 {filled}/{total} 个法律要件，请核实："]

    if profile:
        if 'industry' in profile:
            lines.append(f"· 行业：{profile['industry']}")
        if 'location_hint' in profile:
            lines.append(f"· 德国地点：{profile['location_hint']}")

    # Show which questions were answered
    answered_yes = [str(qid) for qid, ans in answers.items() if ans]
    answered_no = [str(qid) for qid, ans in answers.items() if not ans]

    if answered_yes:
        lines.append(f"· 识别为「是」：Q{', Q'.join(answered_yes)}")
    if answered_no:
        lines.append(f"· 识别为「否」：Q{', Q'.join(answered_no)}")

    unanswered = [str(i) for i in range(1, 16) if i not in answers]
    if unanswered:
        lines.append(f"· 未识别（建议手动补充）：Q{', Q'.join(unanswered)}")

    return '\n'.join(lines)
