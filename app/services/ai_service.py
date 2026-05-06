import re
import anthropic

BMC_SYSTEM = """당신은 비즈니스 모델 설계 전문 컨설턴트입니다.
분석 결과를 순수 HTML로만 반환하세요. 마크다운, 코드블록, 설명 텍스트는 절대 포함하지 마세요.

[출력 규칙]
- 반드시 HTML 태그만 반환 (```html 같은 코드블록 금지)
- 객관적·사실 기반의 전문 컨설턴트 문체 사용
- 표(table), 강도 게이지, 매트릭스, 인사이트 박스 등 시각 요소 적극 활용
- 허용 태그: div, table, thead, tbody, tr, th, td, h3, h4, p, ul, li, span, strong, em
- class 속성 사용 가능 (아래 클래스 목록 활용)
- 인라인 style 최소화, 아래 제공된 CSS 클래스 우선 사용

[사용 가능한 CSS 클래스]
bcg-section        : 섹션 컨테이너
bcg-section-title  : 섹션 제목 (h3)
bcg-table          : 기본 표
bcg-table th       : 표 헤더
bcg-badge-high     : 높음/위험 배지 (빨강 계열)
bcg-badge-mid      : 중간 배지 (주황 계열)
bcg-badge-low      : 낮음/안전 배지 (초록 계열)
bcg-gauge          : 강도 게이지 바 컨테이너
bcg-gauge-fill     : 게이지 채움 (style="width:XX%" 필수)
bcg-insight        : 핵심 인사이트 박스 (파란 강조)
bcg-insight-warn   : 경고 인사이트 박스 (주황 강조)
bcg-matrix-grid    : 2×2 매트릭스 그리드
bcg-matrix-cell    : 매트릭스 셀
bcg-pill           : 작은 태그/키워드 pill
bcg-implication    : 전략적 시사점 항목
bcg-two-col        : 2단 레이아웃
bcg-kv             : key-value 행
bcg-kv-key         : key 셀
bcg-kv-val         : value 셀
bcg-priority-1     : 우선순위 1 (강조)
bcg-priority-2     : 우선순위 2
bcg-priority-3     : 우선순위 3
"""

PROMPTS = {
    # ── STEP 1: 사업 정의 ──────────────────────────────────────────
    'biz_definition': BMC_SYSTEM + """
[분석 대상]
프로젝트: {project_name} / 수행 조직: {organization}

[입력 데이터]
사업 도메인: {biz_domain}
핵심 제품·서비스 범위: {product_scope}
매출 구조 및 주요 고객군: {revenue_customer}
기업 규모 및 보유 역량: {capabilities}
해결하려는 고객 문제: {customer_problem}

[출력 구조 — 아래 3개 산출물을 순서대로 모두 작성하세요]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
산출물 1. 사업 정의서
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<h3 class="bcg-section-title">📄 사업 정의서</h3>

1-1. 핵심사업 정의 (bcg-insight):
     "우리는 [고객군]의 [핵심 문제]를 [제품/서비스]로 해결하는 [도메인] 기업이다." 형식으로 2~3문장 작성

1-2. 사업 정의 구성요소 표 (bcg-table):
     컬럼: 구성요소 | 정의 내용 | 완성도 | 보완 권고
     행: 사업 도메인 / 제품·서비스 범위 / 매출 구조·고객군 / 보유 역량·자산 / 고객 문제
     완성도: bcg-badge-low(충분) / bcg-badge-mid(보통) / bcg-badge-high(보완필요)

1-3. 고객 문제 ↔ 사업 범위 정합성 (bcg-kv):
     고객이 겪는 문제와 제품·서비스 범위의 연결성을 항목별로 평가

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
산출물 2. BMC 초안
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<h3 class="bcg-section-title">🗂️ 비즈니스 모델 캔버스(BMC) 초안</h3>

2-1. BMC 9개 항목 초안 표 (bcg-table):
     컬럼: BMC 항목 | 초안 내용 (입력 데이터 기반 추론 포함) | 신뢰도 | 추가 확인 필요 사항
     행: 가치제안 / 고객세그먼트 / 채널 / 고객관계 / 수익원 / 핵심자원 / 핵심활동 / 핵심파트너십 / 비용구조
     신뢰도: bcg-badge-low(높음) / bcg-badge-mid(중간) / bcg-badge-high(낮음·추론)

2-2. 핵심 가치제안 요약 (bcg-insight):
     가장 차별화된 가치제안 1~2줄 강조

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
산출물 3. 정보 수집 체크리스트
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<h3 class="bcg-section-title">✅ 정보 수집 체크리스트</h3>

3-1. 항목별 수집 필요 정보 표 (bcg-table):
     컬럼: 수집 항목 | 왜 필요한가 | 수집 방법 | 우선순위
     우선순위: bcg-badge-high(즉시) / bcg-badge-mid(단기) / bcg-badge-low(중기)
     BMC 초안에서 신뢰도가 낮은 항목 위주로 5~8개 작성

3-2. 다음 단계 액션 아이템 (bcg-implication 3~5개):
     사업 정의를 완성하기 위해 지금 당장 해야 할 구체적 행동 목록
""",

    # ── STEP 2: 환경 분석 ──────────────────────────────────────────
    'env_analysis': BMC_SYSTEM + """
[분석 대상]
프로젝트: {project_name} / 수행 조직: {organization}

[입력 데이터]
PESTEL 데이터: {pestel_data}
5 Forces 데이터: {five_forces_data}
SWOT 데이터: {swot_data}
VRIO 데이터: {vrio_data}
고객 세그먼트 맵 데이터: {segment_data}

[출력 구조 — 5개 산출물을 순서대로 모두 작성하세요]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
산출물 1. PESTEL 분석
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<h3 class="bcg-section-title">🌍 PESTEL 분석</h3>
1-1. 종합 인사이트 (bcg-insight): 거시환경이 사업에 미치는 영향 2~3문장
1-2. 항목별 분석 표 (bcg-table) 컬럼: 요소 | 주요 내용 | 사업 영향 | 영향도
     행: Political / Economic / Social / Technological / Environmental / Legal
     영향도: bcg-badge-high(높음)/bcg-badge-mid(중간)/bcg-badge-low(낮음)
1-3. 핵심 시사점 (bcg-implication 2~3개)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
산출물 2. 5 Forces 분석
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<h3 class="bcg-section-title">⚔️ 5 Forces 분석</h3>
2-1. 산업 매력도 종합 판단 (bcg-insight 또는 bcg-insight-warn): 2~3문장
2-2. Forces 강도 분석 표 (bcg-table) 컬럼: Forces | 주요 근거 | 강도(bcg-gauge) | 전략적 대응
     행: 기존 경쟁자 경쟁 / 신규 진입 위협 / 대체재 위협 / 구매자 협상력 / 공급자 협상력
2-3. 대응 전략 권고 (bcg-implication 2~3개)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
산출물 3. SWOT 분석표
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<h3 class="bcg-section-title">🔲 SWOT 분석표</h3>
3-1. SWOT 매트릭스 (bcg-matrix-grid 2×2): S/W/O/T 각 셀 3~5개 항목
3-2. SO·ST·WO·WT 전략 도출 표 (bcg-table) 컬럼: 전략 유형 | 핵심 전략 내용 | 우선순위

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
산출물 4. VRIO 분석
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<h3 class="bcg-section-title">🏆 VRIO 분석</h3>
4-1. 종합 평가 인사이트 (bcg-insight): 지속가능한 경쟁우위 보유 여부 2~3문장
4-2. VRIO 자원·역량 평가 표 (bcg-table) 컬럼: 자원/역량 | 가치(V) | 희소성(R) | 모방곤란성(I) | 조직화(O) | 경쟁우위
     경쟁우위: bcg-badge-low(지속적 우위)/bcg-badge-mid(일시적 우위)/bcg-badge-high(열위)
4-3. 핵심 역량 강화 권고 (bcg-implication 2~3개)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
산출물 5. 고객 세그먼트 맵
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<h3 class="bcg-section-title">👥 고객 세그먼트 맵</h3>
5-1. 세그먼트 구조 표 (bcg-table) 컬럼: 세그먼트 | 특성·규모 | 핵심 니즈 | 구매 기준 | 매력도
     매력도: bcg-gauge
5-2. ICP(이상적 고객 프로파일) 요약 (bcg-insight): 최우선 타겟 세그먼트 2~3문장
5-3. 세그먼트별 진입 전략 권고 (bcg-implication 2~3개)
""",

    # ── STEP 3: 가치 설계 ──────────────────────────────────────────
    'value_design': BMC_SYSTEM + """
[분석 대상]
프로젝트: {project_name} / 수행 조직: {organization}

[입력 데이터]
핵심 제품/서비스: {core_product}
차별화 포인트: {differentiation}
고객 경험 여정: {customer_journey}
핵심 자원: {key_resources}
핵심 활동: {key_activities}
핵심 파트너십: {key_partnerships}

[출력 구조]
1. 가치 제안 강도 평가 (bcg-insight): 차별화 수준 종합 판단
2. 비즈니스 모델 구성요소 표 (bcg-table):
   컬럼: 구성요소 | 내용 | 경쟁력 수준 | 강화 방향
   경쟁력은 bcg-gauge로 시각화
3. 고객 여정 단계별 가치 전달 (bcg-kv): 인지→탐색→구매→사용→재구매
4. 핵심 자원·활동·파트너십 연계 (bcg-section): 상호 연결 구조 설명
5. 가치 설계 개선 권고 (bcg-implication 3~4개)
""",

    # ── STEP 4: 수익 구조 ──────────────────────────────────────────
    'revenue_model': BMC_SYSTEM + """
[분석 대상]
프로젝트: {project_name} / 수행 조직: {organization}

[입력 데이터]
수익 모델 유형: {revenue_type}
가격 전략: {pricing}
고객 획득 채널: {channels}
비용 구조: {cost_structure}
단위 경제성(Unit Economics): {unit_economics}
수익성 목표: {profitability_target}

[출력 구조]
1. 수익 구조 건전성 진단 (bcg-insight 또는 bcg-insight-warn): 수익 모델 실현가능성 2~3문장
2. 수익 모델 분석 표 (bcg-table):
   컬럼: 항목 | 내용 | 평가 | 리스크
   평가는 bcg-badge-*
3. 비용 vs 수익 구조 (bcg-two-col): 주요 비용 항목 / 주요 수익원
4. Unit Economics 분석 (bcg-kv): CAC, LTV, 손익분기점 등
5. 수익 구조 최적화 권고 (bcg-implication 3~4개)
""",

    # ── STEP 5: 실행 체계 ──────────────────────────────────────────
    'execution': BMC_SYSTEM + """
[분석 대상]
프로젝트: {project_name} / 수행 조직: {organization}

[입력 데이터]
실행 로드맵 (단계별): {roadmap}
핵심 성과지표 (KPI): {kpi}
조직 및 역할: {organization_structure}
필요 자원 및 예산: {resources_budget}
리스크 및 대응 방안: {risk_management}

[출력 구조]
1. 실행 체계 준비도 평가 (bcg-insight 또는 bcg-insight-warn): 실행 가능성 종합 판단
2. 단계별 로드맵 표 (bcg-table):
   컬럼: 단계 | 기간 | 핵심 과제 | 성공 기준 | 리스크
3. KPI 대시보드 (bcg-kv): 지표명 / 목표값 / 측정 방법
4. 리스크 매트릭스 (bcg-table):
   컬럼: 리스크 | 발생 가능성 | 영향도 | 대응 전략
   발생 가능성·영향도는 bcg-badge-*
5. 실행 체계 강화 권고 (bcg-implication 3~4개)
""",

    # ── STEP 6: 검증·정제 ──────────────────────────────────────────
    'validation': BMC_SYSTEM + """
[분석 대상]
프로젝트: {project_name} / 수행 조직: {organization}

[입력 데이터]
검증 가설 (핵심 가정): {hypotheses}
검증 방법 (MVP/실험): {validation_method}
수집된 데이터/피드백: {feedback_data}
학습 및 인사이트: {learnings}
피벗 또는 개선 사항: {pivot_improvements}

[출력 구조]
1. 비즈니스 모델 검증 종합 평가 (bcg-insight 또는 bcg-insight-warn): 검증 완성도 2~3문장
2. 가설 검증 현황 표 (bcg-table):
   컬럼: 핵심 가설 | 검증 방법 | 결과 | 유효성 | 다음 액션
   유효성은 bcg-badge-low(검증됨)/bcg-badge-mid(부분검증)/bcg-badge-high(미검증)
3. 학습 루프 분석 (bcg-kv): 가설→실험→학습→개선 사이클
4. 피벗/개선 우선순위 매트릭스 (bcg-matrix-grid 2×2):
   축: 영향도(높음/낮음) × 실행 용이성(쉬움/어려움)
5. 비즈니스 모델 최종 개선 권고 (bcg-implication 4~5개, 우선순위 순)
""",
}

MODULE_FIELDS = {
    'biz_definition': [
        ('biz_domain',       '사업 도메인',              '예: B2B SaaS, SI, 플랫폼, 데이터, 커머스, 제조 등'),
        ('product_scope',    '핵심 제품·서비스 범위',    '핵심 제품·서비스의 기능 범위와 제공 방식'),
        ('revenue_customer', '매출 구조 및 주요 고객군', '현재 매출 구조(구독/거래/프로젝트 등)와 주요 고객군'),
        ('capabilities',     '기업 규모 및 보유 역량',   '기업 규모, 핵심 기술·인력·특허 등 보유 자산'),
        ('customer_problem', '해결하려는 고객 문제',     '고객이 실제로 겪고 있는 핵심 불편함과 미충족 니즈'),
    ],
    'env_analysis': [
        ('pestel_data',      '🌍 PESTEL',        '정치·경제·사회·기술·환경·법규 관련 주요 사실과 트렌드를 자유롭게 기입하세요.'),
        ('five_forces_data', '⚔️ 5 Forces',      '기존 경쟁자·신규진입·대체재·구매자·공급자 협상력 현황을 기입하세요.'),
        ('swot_data',        '🔲 SWOT',          '강점·약점·기회·위협 항목을 알고 있는 것 모두 기입하세요.'),
        ('vrio_data',        '🏆 VRIO',          '보유 자원·역량의 가치(V)·희소성(R)·모방곤란성(I)·조직화(O) 여부를 기입하세요.'),
        ('segment_data',     '👥 고객 세그먼트 맵', '타겟 고객 세그먼트, 규모, 핵심 니즈, 구매 기준 등을 기입하세요.'),
    ],
    'value_design': [
        ('core_product',      '핵심 제품/서비스',       '제공하는 제품 또는 서비스의 핵심 기능'),
        ('differentiation',   '차별화 포인트',          '경쟁사 대비 독보적인 차별점'),
        ('customer_journey',  '고객 경험 여정',         '고객이 제품/서비스를 만나는 전체 여정'),
        ('key_resources',     '핵심 자원',              '사업 운영에 필수적인 자산, 기술, 인력'),
        ('key_activities',    '핵심 활동',              '가치 제공을 위한 핵심 프로세스'),
        ('key_partnerships',  '핵심 파트너십',          '사업 성공을 위한 외부 파트너 및 협력 관계'),
    ],
    'revenue_model': [
        ('revenue_type',          '수익 모델 유형',          '구독/거래/광고/라이선스/플랫폼 등'),
        ('pricing',               '가격 전략',               '가격 책정 기준, 가격 포지셔닝'),
        ('channels',              '고객 획득 채널',           '마케팅·영업 채널 및 고객 유입 경로'),
        ('cost_structure',        '비용 구조',               '고정비/변동비, 주요 비용 항목'),
        ('unit_economics',        '단위 경제성 (Unit Economics)', 'CAC, LTV, 마진율, 손익분기점'),
        ('profitability_target',  '수익성 목표',              '목표 매출, 영업이익률, 흑자 전환 시점'),
    ],
    'execution': [
        ('roadmap',                '실행 로드맵',         '단계별 일정, 마일스톤, 출시 계획'),
        ('kpi',                    '핵심 성과지표 (KPI)', '측정 가능한 성과 지표와 목표값'),
        ('organization_structure', '조직 및 역할',        '팀 구성, 핵심 인력, 역할 분담'),
        ('resources_budget',       '필요 자원 및 예산',   '인력·기술·자금 등 필요 자원과 예산'),
        ('risk_management',        '리스크 및 대응 방안', '주요 리스크와 완화 전략'),
    ],
    'validation': [
        ('hypotheses',         '검증 가설 (핵심 가정)', '사업 성공을 위한 핵심 가정과 가설'),
        ('validation_method',  '검증 방법 (MVP/실험)',  'MVP, 파일럿, A/B테스트 등 검증 방식'),
        ('feedback_data',      '수집된 데이터/피드백',  '실제 고객 반응, 실험 결과, 수집 데이터'),
        ('learnings',          '학습 및 인사이트',      '검증 과정에서 얻은 핵심 배움'),
        ('pivot_improvements', '피벗 또는 개선 사항',   '모델 수정, 방향 전환, 개선 계획'),
    ],
}

ASK_MAX_TOKENS = 1500
ANALYZE_MAX_TOKENS = 15000
ASK_ALL_MAX_TOKENS = 3000


def ask_all_fields_with_claude(module_type: str, question: str, project_name: str, organization: str) -> dict:
    fields = MODULE_FIELDS.get(module_type, [])
    if not fields:
        return {'error': '지원하지 않는 모듈 유형입니다.'}

    field_list = '\n'.join(
        f'- {fname}: {label} ({desc})' for fname, label, desc in fields
    )
    field_example = '{' + ', '.join(f'"{fname}": "내용"' for fname, _, _ in fields) + '}'

    system = (
        f"당신은 비즈니스 모델 설계 전문가입니다. "
        f"프로젝트명: {project_name}, 수행 조직: {organization or '미입력'}. "
        "사용자의 질문/상황 설명을 바탕으로 각 입력 필드에 바로 붙여넣을 수 있는 "
        "구체적이고 실용적인 내용을 작성해주세요. "
        f"반드시 다음 JSON 형식으로만 응답하세요 (다른 텍스트 없이 JSON만):\n{field_example}\n"
        "각 필드 값은 2~5문장의 구체적인 내용으로 작성하세요. "
        "JSON 외의 설명, 마크다운, 코드블록은 절대 포함하지 마세요."
    )

    try:
        from flask import current_app
        api_key = current_app.config.get('ANTHROPIC_API_KEY', '')
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model='claude-opus-4-6',
            max_tokens=ASK_ALL_MAX_TOKENS,
            system=system,
            messages=[{
                'role': 'user',
                'content': (
                    f"다음 상황을 바탕으로 각 항목을 작성해주세요.\n\n"
                    f"[사용자 입력]\n{question}\n\n"
                    f"[작성할 필드]\n{field_list}\n\n"
                    f"응답 형식: {field_example}"
                )
            }]
        )
        raw = message.content[0].text.strip()
        raw = re.sub(r'^```[a-z]*\n?', '', raw)
        raw = re.sub(r'\n?```$', '', raw)
        import json
        return json.loads(raw)
    except Exception as e:
        return {'error': f'오류가 발생했습니다: {str(e)}'}


def ask_field_with_claude(_module_type: str, field_label: str, question: str, project_name: str, organization: str) -> str:
    system = (
        f"당신은 비즈니스 모델 설계 전문가입니다. "
        f"프로젝트명: {project_name}, 수행 조직: {organization or '미입력'}. "
        f"사용자가 '{field_label}' 항목 입력을 위해 질문합니다. "
        f"응답은 최대 {ASK_MAX_TOKENS} 토큰 이내에서 완결되어야 합니다. "
        "답변이 길어질 경우 핵심 내용 위주로 요약하여 반드시 완전한 문장으로 마무리하세요. "
        "마지막에 '--- 입력 제안 ---' 구분선 이후에 "
        "해당 필드에 바로 붙여넣을 수 있는 간결한 텍스트를 제안하세요."
    )
    try:
        from flask import current_app
        api_key = current_app.config.get('ANTHROPIC_API_KEY', '')
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model='claude-opus-4-6',
            max_tokens=ASK_MAX_TOKENS,
            system=system,
            messages=[{'role': 'user', 'content': question}]
        )
        return message.content[0].text
    except Exception as e:
        return f'오류가 발생했습니다: {str(e)}'


ENV_ANALYSIS_SUB_PROMPTS = {
    'pestel': BMC_SYSTEM + """
[분석 대상]
프로젝트: {project_name} / 수행 조직: {organization}
[입력 데이터]
PESTEL 데이터: {pestel_data}
[출력 구조]
<h3 class="bcg-section-title">🌍 PESTEL 분석</h3>
1. 종합 인사이트 (bcg-insight): 거시환경이 사업에 미치는 영향 2~3문장
2. 항목별 분석 표 (bcg-table) 컬럼: 요소 | 주요 내용 | 사업 영향 | 영향도
   행: Political(정책) / Economic(경제) / Social(사회) / Technological(기술) / Environmental(환경) / Legal(법규)
   영향도: bcg-badge-high(높음)/bcg-badge-mid(중간)/bcg-badge-low(낮음)
3. 핵심 시사점 (bcg-implication 2~3개)
""",
    'five_forces': BMC_SYSTEM + """
[분석 대상]
프로젝트: {project_name} / 수행 조직: {organization}
[입력 데이터]
5 Forces 데이터: {five_forces_data}
[출력 구조]
<h3 class="bcg-section-title">⚔️ 5 Forces 분석</h3>
1. 산업 매력도 종합 판단 (bcg-insight 또는 bcg-insight-warn): 2~3문장
2. Forces 강도 분석 표 (bcg-table) 컬럼: Forces | 주요 근거 | 강도(bcg-gauge) | 전략적 대응
   행: 기존 경쟁자 경쟁 / 신규 진입 위협 / 대체재 위협 / 구매자 협상력 / 공급자 협상력
3. 대응 전략 권고 (bcg-implication 2~3개)
""",
    'swot': BMC_SYSTEM + """
[분석 대상]
프로젝트: {project_name} / 수행 조직: {organization}
[입력 데이터]
SWOT 데이터: {swot_data}
[출력 구조]
<h3 class="bcg-section-title">🔲 SWOT 분석표</h3>
1. SWOT 매트릭스 (bcg-matrix-grid 2×2): S/W/O/T 각 셀 3~5개 항목
2. SO·ST·WO·WT 전략 도출 표 (bcg-table) 컬럼: 전략 유형 | 핵심 전략 내용 | 우선순위
   행: SO전략 / ST전략 / WO전략 / WT전략
""",
    'vrio': BMC_SYSTEM + """
[분석 대상]
프로젝트: {project_name} / 수행 조직: {organization}
[입력 데이터]
VRIO 데이터: {vrio_data}
[출력 구조]
<h3 class="bcg-section-title">🏆 VRIO 분석</h3>
1. 종합 평가 인사이트 (bcg-insight): 지속가능한 경쟁우위 보유 여부 2~3문장
2. VRIO 자원·역량 평가 표 (bcg-table) 컬럼: 자원/역량 | 가치(V) | 희소성(R) | 모방곤란성(I) | 조직화(O) | 경쟁우위
   경쟁우위: bcg-badge-low(지속적 우위)/bcg-badge-mid(일시적 우위)/bcg-badge-high(열위)
3. 핵심 역량 강화 권고 (bcg-implication 2~3개)
""",
    'segment': BMC_SYSTEM + """
[분석 대상]
프로젝트: {project_name} / 수행 조직: {organization}
[입력 데이터]
고객 세그먼트 맵 데이터: {segment_data}
[출력 구조]
<h3 class="bcg-section-title">👥 고객 세그먼트 맵</h3>
1. 세그먼트 구조 표 (bcg-table) 컬럼: 세그먼트 | 특성·규모 | 핵심 니즈 | 구매 기준 | 매력도(bcg-gauge)
2. ICP(이상적 고객 프로파일) 요약 (bcg-insight): 최우선 타겟 세그먼트 2~3문장
3. 세그먼트별 진입 전략 권고 (bcg-implication 2~3개)
""",
}

# env_analysis 서브타입 → 필요한 입력 필드 매핑
_ENV_SUB_FIELDS = {
    'pestel':      ['pestel_data'],
    'five_forces': ['five_forces_data'],
    'swot':        ['swot_data'],
    'vrio':        ['vrio_data'],
    'segment':     ['segment_data'],
}


def analyze_with_claude(module_type: str, input_data: dict, project_name: str, industry: str, extra_prompt: str = '', sub_type: str = '') -> str:
    # env_analysis 항목별 단독 분석
    if module_type == 'env_analysis' and sub_type and sub_type in ENV_ANALYSIS_SUB_PROMPTS:
        prompt_template = ENV_ANALYSIS_SUB_PROMPTS[sub_type]
        needed = _ENV_SUB_FIELDS.get(sub_type, [])
        filtered = {k: input_data.get(k, '(미입력)') or '(미입력)' for k in needed}
        try:
            prompt = prompt_template.format(
                project_name=project_name,
                organization=industry or '미입력',
                **filtered
            )
        except KeyError:
            prompt = prompt_template.replace('{project_name}', project_name).replace('{organization}', industry or '미입력')
            for k, v in filtered.items():
                prompt = prompt.replace('{' + k + '}', v)
            prompt = re.sub(r'\{[^}]+\}', '(미입력)', prompt)
        try:
            from flask import current_app
            api_key = current_app.config.get('ANTHROPIC_API_KEY', '')
            client = anthropic.Anthropic(api_key=api_key)
            message = client.messages.create(
                model='claude-opus-4-6',
                max_tokens=ANALYZE_MAX_TOKENS,
                messages=[{'role': 'user', 'content': prompt}]
            )
            result = message.content[0].text.strip()
            if result.startswith('```'):
                result = re.sub(r'^```[a-z]*\n?', '', result)
                result = re.sub(r'\n?```$', '', result)
            return result
        except Exception as e:
            raise RuntimeError(str(e)) from e

    prompt_template = PROMPTS.get(module_type)
    if not prompt_template:
        return '지원하지 않는 모듈 유형입니다.'

    try:
        prompt = prompt_template.format(
            project_name=project_name,
            organization=industry or '미입력',
            **{k: v or '(미입력)' for k, v in input_data.items()}
        )
    except KeyError:
        prompt = prompt_template.replace('{project_name}', project_name).replace('{organization}', industry or '미입력')
        for key, value in input_data.items():
            prompt = prompt.replace('{' + key + '}', value or '(미입력)')
        prompt = re.sub(r'\{[^}]+\}', '(미입력)', prompt)

    if extra_prompt and extra_prompt.strip():
        prompt += f'\n\n[추가 분석 지시사항]\n{extra_prompt.strip()}'

    try:
        from flask import current_app
        api_key = current_app.config.get('ANTHROPIC_API_KEY', '')
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model='claude-opus-4-6',
            max_tokens=ANALYZE_MAX_TOKENS,
            messages=[{'role': 'user', 'content': prompt}]
        )
        result = message.content[0].text.strip()
        if result.startswith('```'):
            result = re.sub(r'^```[a-z]*\n?', '', result)
            result = re.sub(r'\n?```$', '', result)

        if message.stop_reason == 'max_tokens':
            shorten_prompt = (
                "아래는 분석 결과 HTML인데, 토큰 한도 초과로 잘렸습니다. "
                "15000 토큰 이내에 완전히 완결되도록 핵심 내용 위주로 축약해 주세요. "
                "출력 규칙: 순수 HTML만, 코드블록 금지, 모든 태그 정상 닫힘 필수.\n\n"
                f"{result}"
            )
            shorten_msg = client.messages.create(
                model='claude-opus-4-6',
                max_tokens=ANALYZE_MAX_TOKENS,
                messages=[{'role': 'user', 'content': shorten_prompt}]
            )
            result = shorten_msg.content[0].text.strip()
            if result.startswith('```'):
                result = re.sub(r'^```[a-z]*\n?', '', result)
                result = re.sub(r'\n?```$', '', result)

        return result
    except Exception as e:
        raise RuntimeError(str(e)) from e
