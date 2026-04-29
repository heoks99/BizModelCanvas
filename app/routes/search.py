import json
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from app.models.project import Project, Analysis

search_bp = Blueprint('search', __name__)

MODULE_NAMES = {
    'pestel':        '① PESTEL 분석',
    'five_forces':   '② Porter\'s 5 Forces',
    'swot':          '③ SWOT 분석',
    'ansoff':        '④ Ansoff Matrix',
    'horizons':      '⑤ 3 Horizons 모델',
    'ogsm':          '⑥ OGSM 실행 계획서',
    'result_report': '⑦ 성과 분석 리포트',
}


@search_bp.route('/search')
@login_required
def search():
    query = request.args.get('q', '').strip()
    results = []

    if query:
        projects = Project.query.filter_by(owner_id=current_user.id).all()

        for project in projects:
            # 프로젝트명/설명 검색
            proj_score = 0
            if query.lower() in project.name.lower():
                proj_score += 2
            if project.description and query.lower() in project.description.lower():
                proj_score += 1

            if proj_score:
                results.append({
                    'type': 'project',
                    'score': proj_score,
                    'project': project,
                    'title': project.name,
                    'snippet': project.description or '',
                    'url': f'/projects/{project.id}',
                })

            # 분석 모듈 내용 검색
            for analysis in project.analyses:
                score = 0
                snippets = []

                # 입력 데이터 검색
                if analysis.input_data:
                    try:
                        input_data = json.loads(analysis.input_data)
                        for val in input_data.values():
                            if val and query.lower() in val.lower():
                                score += 1
                                idx = val.lower().find(query.lower())
                                start = max(0, idx - 40)
                                end = min(len(val), idx + len(query) + 60)
                                snippet = ('…' if start > 0 else '') + val[start:end] + ('…' if end < len(val) else '')
                                snippets.append(snippet)
                    except Exception:
                        pass

                # AI 분석 결과 검색 (HTML 태그 제거 후)
                if analysis.ai_result:
                    import re
                    plain = re.sub(r'<[^>]+>', ' ', analysis.ai_result)
                    plain = re.sub(r'\s+', ' ', plain).strip()
                    if query.lower() in plain.lower():
                        score += 1
                        idx = plain.lower().find(query.lower())
                        start = max(0, idx - 40)
                        end = min(len(plain), idx + len(query) + 60)
                        snippet = ('…' if start > 0 else '') + plain[start:end] + ('…' if end < len(plain) else '')
                        snippets.append(snippet)

                if score:
                    results.append({
                        'type': 'analysis',
                        'score': score,
                        'project': project,
                        'module_type': analysis.module_type,
                        'module_name': MODULE_NAMES.get(analysis.module_type, analysis.module_type),
                        'title': f'{project.name} — {MODULE_NAMES.get(analysis.module_type, analysis.module_type)}',
                        'snippets': snippets[:2],
                        'url': f'/projects/{project.id}/modules/{analysis.module_type}',
                    })

        results.sort(key=lambda r: r['score'], reverse=True)

    return render_template('search/results.html', query=query, results=results)
