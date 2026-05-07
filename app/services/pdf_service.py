import io
import json
import os
import re
from datetime import datetime
from xhtml2pdf import pisa, default as xpdf_default
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily

# 폰트 경로: 프로젝트 내장 → Windows 시스템 순으로 탐색
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FONT_CANDIDATES = [
    # 프로젝트 내장 (Railway/Linux 포함 모든 환경)
    os.path.join(_BASE_DIR, 'static', 'fonts', 'malgun.ttf'),
    os.path.join(_BASE_DIR, 'static', 'fonts', 'malgunbd.ttf'),
    # Windows 시스템
    'C:/Windows/Fonts/malgun.ttf',
    'C:/Windows/Fonts/malgunbd.ttf',
]

def _find_font(name):
    for path in _FONT_CANDIDATES:
        if name in os.path.basename(path) and os.path.exists(path):
            return path
    return None

try:
    normal_path = _find_font('malgun.ttf')
    bold_path   = _find_font('malgunbd.ttf')
    if not normal_path or not bold_path:
        raise FileNotFoundError('malgun font not found')
    pdfmetrics.registerFont(TTFont('malgun',   normal_path))
    pdfmetrics.registerFont(TTFont('malgunbd', bold_path))
    registerFontFamily('malgun',
                       normal='malgun', bold='malgunbd',
                       italic='malgun', boldItalic='malgunbd')
    xpdf_default.DEFAULT_FONT['malgun']   = 'malgun'
    xpdf_default.DEFAULT_FONT['malgunbd'] = 'malgunbd'
    KOREAN_FONT = 'malgun'
except Exception as _e:
    KOREAN_FONT = 'Helvetica'

# 모듈 메타 정보
MODULE_META = {
    'biz_definition': {'name': '사업 정의', 'icon': '🎯'},
    'env_analysis':   {'name': '환경 분석', 'icon': '🌐'},
    'value_design':   {'name': '가치 설계', 'icon': '💡'},
    'revenue_model':  {'name': '수익 구조', 'icon': '💰'},
    'execution':      {'name': '실행 체계', 'icon': '🚀'},
    'validation':     {'name': '검증·정제', 'icon': '🔬'},
}


# BCG CSS 클래스 → xhtml2pdf 호환 인라인 스타일 매핑
_BCG_CLASS_STYLES = {
    'bcg-section':       'margin-bottom:14px;',
    'bcg-section-title': 'font-size:11pt;font-weight:bold;color:#4f6ef7;border-bottom:2px solid #4f6ef7;padding-bottom:4px;margin:14px 0 8px;',
    'bcg-table':         'width:100%;border-collapse:collapse;font-size:9pt;margin-bottom:12px;',
    'bcg-insight':       'background:#eef2ff;border-left:4px solid #4f6ef7;padding:8px 12px;margin:10px 0;font-size:9pt;',
    'bcg-insight-warn':  'background:#fff8ee;border-left:4px solid #f5a623;padding:8px 12px;margin:10px 0;font-size:9pt;',
    'bcg-badge-high':    'background:#fee2e2;color:#b91c1c;padding:2px 6px;font-size:8pt;font-weight:bold;',
    'bcg-badge-mid':     'background:#fef3c7;color:#92400e;padding:2px 6px;font-size:8pt;font-weight:bold;',
    'bcg-badge-low':     'background:#d1fae5;color:#065f46;padding:2px 6px;font-size:8pt;font-weight:bold;',
    'bcg-gauge':         'background:#e5e7eb;height:10px;width:100%;display:block;margin:2px 0;',
    'bcg-gauge-fill':    'height:10px;display:block;',
    'bcg-implication':   'border-left:3px solid #4f6ef7;padding:4px 10px;margin:6px 0;font-size:9pt;',
    'bcg-two-col':       'width:100%;',
    'bcg-kv':            'border-bottom:1px solid #eee;padding:4px 0;font-size:9pt;',
    'bcg-kv-key':        'font-weight:bold;color:#333;padding-right:8px;width:35%;',
    'bcg-kv-val':        'color:#555;',
    'bcg-matrix-grid':   'width:100%;border-collapse:collapse;',
    'bcg-matrix-cell':   'border:1px solid #c7d2fe;background:#f8f9ff;padding:8px;vertical-align:top;font-size:9pt;width:50%;',
    'bcg-pill':          'background:#e0e7ff;color:#3730a3;padding:1px 6px;font-size:8pt;margin:1px;',
    'bcg-priority-1':    'color:#dc2626;font-weight:bold;',
    'bcg-priority-2':    'color:#d97706;font-weight:bold;',
    'bcg-priority-3':    'color:#059669;font-weight:bold;',
}

# table/th/td 기본 스타일 (class 없는 태그용)
_TABLE_TAG_CSS = (
    "table { width:100%; border-collapse:collapse; font-size:9pt; margin-bottom:12px; }\n"
    "th { background:#4f6ef7; color:white; padding:5px 8px; text-align:left; font-size:9pt; }\n"
    "td { border:1px solid #dde3ff; padding:5px 8px; vertical-align:top; font-size:9pt; }\n"
    "tr:nth-child(even) td { background:#f8f9ff; }\n"
    "h3 { font-size:10pt; font-weight:bold; color:#4f6ef7; margin:10px 0 6px; }\n"
    "h4 { font-size:9.5pt; font-weight:bold; color:#333; margin:8px 0 4px; }\n"
    "ul { margin:4px 0 4px 14px; padding:0; }\n"
    "li { margin-bottom:2px; }\n"
    "p { margin:0 0 6px; }\n"
)


def sanitize_bcg_html_for_pdf(html_text):
    """BCG HTML의 class 속성을 xhtml2pdf 호환 인라인 style로 변환."""
    if not html_text:
        return ''

    # gauge용 inline-block → block 으로 교체 (xhtml2pdf는 inline-block 미지원)
    # gauge div 바깥에 씌워진 "display:inline-block; width:60%;" 패턴을 테이블로 대체하기 전에
    # 단순히 display:block 으로 정규화
    html_text = re.sub(
        r'display\s*:\s*inline-block\s*;?\s*',
        'display:block;',
        html_text,
        flags=re.IGNORECASE
    )

    def replace_class(m):
        tag_open = m.group(1)   # 태그명 + class 앞의 속성들
        classes  = m.group(2)   # class 값
        rest     = m.group(3)   # class 뒤 나머지 속성들 (닫는 > 제외)

        styles = []
        for cls in classes.split():
            if cls in _BCG_CLASS_STYLES:
                styles.append(_BCG_CLASS_STYLES[cls])

        # 기존 style 속성이 있으면 맨 앞에 합치기
        existing_style = re.search(r'style=["\']([^"\']*)["\']', rest)
        if existing_style:
            styles.insert(0, existing_style.group(1))
            rest = re.sub(r'\s*style=["\'][^"\']*["\']', '', rest)

        style_attr = ' style="' + ' '.join(styles) + '"' if styles else ''
        # 닫는 > 를 반드시 추가
        return f'<{tag_open}{style_attr}{rest}>'

    result = re.sub(
        r'<(\w+[^>]*?)\s+class=["\']([^"\']+)["\']([^>]*)>',
        replace_class,
        html_text,
        flags=re.IGNORECASE
    )

    # gauge 섹션을 xhtml2pdf 호환 단순 표현으로 변환
    result = _convert_gauge_to_simple(result)

    return result


def _convert_gauge_to_simple(html_text):
    """inline-block gauge 구조를 xhtml2pdf 호환 단순 텍스트 바로 변환."""
    def gauge_replacer(m):
        label      = m.group(1).strip()
        fill_style = m.group(2)
        pct_text   = m.group(3).strip()

        # fill 색상 추출
        bg_m = re.search(r'background\s*:\s*(#[0-9a-fA-F]{3,6})', fill_style)
        bg_color = bg_m.group(1) if bg_m else '#4f6ef7'

        # 퍼센트 숫자 추출
        pct_m = re.search(r'(\d+)', pct_text)
        pct = int(pct_m.group(1)) if pct_m else 0

        # 블록 문자(█)로 게이지 표현 — xhtml2pdf 안전
        filled = round(pct / 5)   # 100% → 20개 블록
        bar = '█' * filled + '░' * (20 - filled)

        return (
            f'<p style="margin:3px 0; font-size:9pt;">'
            f'<strong style="display:block; width:140pt;">{label}</strong>'
            f'<span style="font-family:monospace; color:{bg_color}; letter-spacing:1px;">{bar}</span>'
            f'<span style="font-size:8pt; color:#555; margin-left:6px;"> {pct_text}</span>'
            f'</p>'
        )

    # span 레이블 + 바깥 gauge div + 안쪽 fill div 쌍 매칭
    pattern = (
        r'<span[^>]*>'           # 레이블 span
        r'([^<]+)'               # 레이블 텍스트
        r'</span>\s*'
        r'<div[^>]*>'            # 바깥 gauge div (style 이미 변환됨)
        r'\s*<div[^>]*?style=["\']([^"\']*)["\']>'  # fill div + style 캡처
        r'\s*([^<]*?)\s*'        # "N %" 텍스트
        r'</div>\s*</div>'
    )
    return re.sub(pattern, gauge_replacer, html_text, flags=re.IGNORECASE | re.DOTALL)


PDF_CSS = (
    "@page { size: A4 landscape; margin: 16mm 18mm 18mm 18mm; }\n"
    "body { font-family: " + KOREAN_FONT + "; font-size: 10pt; color: #1a1a2e; line-height: 1.6; }\n"
    + _TABLE_TAG_CSS +
    ".cover { text-align: center; padding: 60px 0 40px; border-bottom: 3px solid #4f6ef7; margin-bottom: 30px; }\n"
    ".cover-badge { display: inline-block; background: #4f6ef7; color: white; font-size: 9pt; font-weight: bold; padding: 4px 14px; border-radius: 20px; margin-bottom: 16px; }\n"
    ".cover-title { font-size: 22pt; font-weight: bold; color: #1a1a2e; margin: 0 0 8px; }\n"
    ".cover-subtitle { font-size: 11pt; color: #555; margin: 0 0 24px; }\n"
    ".cover-meta { font-size: 9pt; color: #777; line-height: 2; }\n"
    ".cover-meta strong { color: #333; }\n"
    ".section-title { font-size: 15pt; font-weight: bold; color: #4f6ef7; border-bottom: 2px solid #4f6ef7; padding-bottom: 6px; margin: 28px 0 16px; page-break-after: avoid; }\n"
    ".module-section { page-break-before: always; }\n"
    ".module-header { background: #f0f3ff; border-left: 4px solid #4f6ef7; padding: 10px 14px; margin-bottom: 16px; page-break-after: avoid; }\n"
    ".module-header h2 { font-size: 13pt; font-weight: bold; color: #1a1a2e; margin: 0 0 2px; }\n"
    ".module-header p { font-size: 9pt; color: #666; margin: 0; }\n"
    ".ai-result-content { font-size: 10pt; color: #333; line-height: 1.7; }\n"
    ".ai-result-content h2 { font-size: 11pt; color: #4f6ef7; margin: 12px 0 6px; }\n"
    ".ai-result-content h3 { font-size: 10pt; color: #333; font-weight: bold; margin: 10px 0 4px; }\n"
    ".ai-result-content h4 { font-size: 10pt; color: #555; font-weight: bold; margin: 8px 0 4px; }\n"
    ".ai-result-content ul { margin: 6px 0 6px 16px; padding: 0; }\n"
    ".ai-result-content li { margin-bottom: 3px; }\n"
    ".ai-result-content strong { color: #1a1a2e; }\n"
    ".ai-result-content p { margin: 0 0 8px; }\n"
    ".no-result { color: #aaa; font-style: italic; font-size: 9pt; }\n"
    ".toc { margin: 20px 0 30px; }\n"
    ".toc-item { padding: 5px 0; border-bottom: 1px dotted #ddd; font-size: 10pt; }\n"
    ".toc-num { color: #4f6ef7; font-weight: bold; margin-right: 8px; }\n"
    ".toc-status { font-size: 9pt; color: #888; }\n"
    ".status-done { color: #3ecf8e; font-weight: bold; }\n"
    ".status-empty { color: #ccc; }\n"
)


ENV_SUB_LABELS = {
    'pestel':      'PESTEL 분석',
    'five_forces': '5 Forces 분석',
    'swot':        'SWOT 분석',
    'vrio':        'VRIO 분석',
    'segment':     '고객 세그먼트 맵',
}
ENV_SUB_ORDER = ['pestel', 'five_forces', 'swot', 'vrio', 'segment']


def _unescape_attr_quotes(html_text: str) -> str:
    """JSON 직렬화 후 남은 \" → " 로 복원하고, attr=&quot;val&quot; 패턴도 정규화."""
    if not html_text:
        return html_text
    # \" → " (JSON에서 파싱된 HTML 속성에 남은 백슬래시 이스케이프)
    html_text = html_text.replace('\\"', '"')
    # &quot; → " (HTML 엔티티 형태)
    html_text = html_text.replace('&quot;', '"')
    return html_text


def _extract_html(module_type: str, ai_result: str) -> str:
    """env_analysis는 JSON dict로 저장되므로 각 sub_type HTML을 합쳐서 반환."""
    if not ai_result:
        return ''
    if module_type == 'env_analysis' and ai_result.strip().startswith('{'):
        try:
            d = json.loads(ai_result)
            parts = []
            for key in ENV_SUB_ORDER:
                val = d.get(key, '')
                if val:
                    label = ENV_SUB_LABELS.get(key, key)
                    parts.append(f'<h3 class="bcg-section-title">{label}</h3>')
                    parts.append(_unescape_attr_quotes(val))
            return '\n'.join(parts)
        except Exception:
            pass
    return _unescape_attr_quotes(ai_result)


def build_module_html(module_type, ai_result):
    meta = MODULE_META.get(module_type, {'name': module_type, 'icon': ''})

    html = f'<div class="module-section">'
    html += f'''<div class="module-header">
        <h2>{meta["name"]}</h2>
    </div>'''

    clean_html = _extract_html(module_type, ai_result)
    if clean_html:
        html += f'<div class="ai-result-content">{sanitize_bcg_html_for_pdf(clean_html)}</div>'
    else:
        html += '<div class="no-result">AI 분석 결과가 없습니다. 모듈에서 AI 분석을 실행해주세요.</div>'

    html += '</div>'
    return html


def generate_module_pdf(project, module_type, ai_result):
    meta = MODULE_META.get(module_type, {'name': module_type, 'icon': ''})
    now = datetime.now().strftime('%Y년 %m월 %d일')

    cover_html = f'''
    <div class="cover">
        <div class="cover-badge">사업모델캔버스</div>
        <h1 class="cover-title">{project.name}</h1>
        <p class="cover-subtitle">{meta["name"]}</p>
        <div class="cover-meta">
            {'<strong>수행 조직</strong>: ' + project.organization + '<br/>' if project.organization else ''}
            {'<strong>사업 담당</strong>: ' + project.business_manager + '<br/>' if project.business_manager else ''}
            {'<strong>수행 담당</strong>: ' + project.project_manager + '<br/>' if project.project_manager else ''}
            <strong>출력일</strong>: {now}
        </div>
    </div>
    '''

    body = build_module_html(module_type, ai_result)

    html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"/>
<style>{PDF_CSS}</style>
</head>
<body>
{cover_html}
{body}
</body>
</html>'''

    buf = io.BytesIO()
    pisa.CreatePDF(io.BytesIO(html.encode('utf-8')), dest=buf)
    buf.seek(0)
    return buf


def generate_full_report_pdf(project, modules, analyses):
    now = datetime.now().strftime('%Y년 %m월 %d일')

    # 표지
    cover_html = f'''
    <div class="cover">
        <div class="cover-badge">사업모델캔버스 — 전체 분석 리포트</div>
        <h1 class="cover-title">{project.name}</h1>
        <p class="cover-subtitle">전략 분석 통합 보고서</p>
        <div class="cover-meta">
            {'<strong>수행 조직</strong>: ' + project.organization + '<br/>' if project.organization else ''}
            {'<strong>사업 담당</strong>: ' + project.business_manager + '<br/>' if project.business_manager else ''}
            {'<strong>수행 담당</strong>: ' + project.project_manager + '<br/>' if project.project_manager else ''}
            {'<strong>프로젝트 설명</strong>: ' + project.description + '<br/>' if project.description else ''}
            <strong>출력일</strong>: {now}
        </div>
    </div>
    '''

    # 목차
    toc_html = '<div class="section-title">목차</div><div class="toc">'
    for i, module in enumerate(modules, 1):
        analysis = analyses.get(module['key'])
        if analysis and analysis.ai_result:
            status = '<span class="status-done">AI 분석 완료</span>'
        elif analysis and analysis.input_data:
            status = '<span class="status-saved">데이터 입력됨</span>'
        else:
            status = '<span class="status-empty">미작성</span>'
        toc_html += f'''<div class="toc-item">
            <span><span class="toc-num">{i:02d}</span><span class="toc-name">{module["name"]}</span></span>
            <span class="toc-status">{status}</span>
        </div>'''
    toc_html += '</div>'

    # 각 모듈 본문
    modules_html = ''
    for module in modules:
        analysis = analyses.get(module['key'])
        ai_result = analysis.ai_result if analysis else None
        modules_html += build_module_html(module['key'], ai_result)

    html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"/>
<style>{PDF_CSS}</style>
</head>
<body>
{cover_html}
{toc_html}
{modules_html}
</body>
</html>'''

    buf = io.BytesIO()
    pisa.CreatePDF(io.BytesIO(html.encode('utf-8')), dest=buf)
    buf.seek(0)
    return buf
