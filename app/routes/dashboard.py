from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.project import Project, Analysis
from datetime import datetime

dashboard_bp = Blueprint('dashboard', __name__)

MODULES = [
    {'key': 'biz_definition', 'step': '①', 'name': '사업 정의', 'icon': '🎯', 'desc': '사업 개요·고객·가치 제안 정의'},
    {'key': 'env_analysis',   'step': '②', 'name': '환경 분석', 'icon': '🌐', 'desc': '시장·경쟁·트렌드 분석'},
    {'key': 'value_design',   'step': '③', 'name': '가치 설계', 'icon': '💡', 'desc': '제품·차별화·파트너십 설계'},
    {'key': 'revenue_model',  'step': '④', 'name': '수익 구조', 'icon': '💰', 'desc': '수익 모델·가격·비용 구조'},
    {'key': 'execution',      'step': '⑤', 'name': '실행 체계', 'icon': '🚀', 'desc': '로드맵·KPI·리스크 관리'},
    {'key': 'validation',     'step': '⑥', 'name': '검증·정제', 'icon': '🔬', 'desc': '가설 검증·학습·피벗'},
]


@dashboard_bp.route('/')
@login_required
def index():
    my_projects = Project.query.filter_by(owner_id=current_user.id).order_by(Project.updated_at.desc()).all()
    public_projects = Project.query.filter(
        Project.is_public == True,
        Project.owner_id != current_user.id
    ).order_by(Project.updated_at.desc()).all()

    orgs = {}
    for p in my_projects:
        key = p.organization or '미지정'
        orgs.setdefault(key, []).append(p)

    return render_template('dashboard/index.html',
                           projects=my_projects,
                           public_projects=public_projects,
                           orgs=orgs)


@dashboard_bp.route('/projects/new', methods=['GET', 'POST'])
@login_required
def new_project():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        organization = request.form.get('organization', '').strip()
        business_manager = request.form.get('business_manager', '').strip()
        project_manager = request.form.get('project_manager', '').strip()
        is_public = request.form.get('is_public') == '1'

        if not name:
            flash('프로젝트 이름을 입력해주세요.', 'error')
        else:
            project = Project(
                name=name,
                description=description,
                organization=organization,
                business_manager=business_manager,
                project_manager=project_manager,
                owner_id=current_user.id,
                is_public=is_public,
            )
            db.session.add(project)
            db.session.commit()
            flash(f'"{name}" 프로젝트가 생성되었습니다.', 'success')
            return redirect(url_for('dashboard.project_detail', project_id=project.id))

    return render_template('dashboard/new_project.html')


@dashboard_bp.route('/projects/<int:project_id>', methods=['GET', 'POST'])
@dashboard_bp.route('/projects/<int:project_id>/<tab_key>', methods=['GET', 'POST'])
@login_required
def project_detail(project_id, tab_key=None):
    import json
    project = Project.query.filter_by(id=project_id).first_or_404()
    is_owner = project.owner_id == current_user.id
    if not is_owner and not project.is_public:
        flash('접근 권한이 없습니다.', 'error')
        return redirect(url_for('dashboard.index'))

    valid_keys = [m['key'] for m in MODULES]
    active_tab = tab_key if tab_key in valid_keys else valid_keys[0]

    analyses = {a.module_type: a for a in project.analyses}

    if request.method == 'POST' and is_owner:
        from app import db
        form_data = request.form.to_dict()
        env_sub_key = form_data.pop('_env_sub_key', '')  # 내부 제어용, DB 저장 제외
        analysis = Analysis.query.filter_by(project_id=project_id, module_type=active_tab).first()
        if not analysis:
            analysis = Analysis(project_id=project_id, module_type=active_tab)
            db.session.add(analysis)
        analysis.input_data = json.dumps(form_data, ensure_ascii=False)
        db.session.commit()
        flash('데이터가 저장되었습니다.', 'success')
        redirect_url = url_for('dashboard.project_detail', project_id=project_id, tab_key=active_tab)
        if env_sub_key:
            redirect_url += f'#env-sub-{env_sub_key}'
        return redirect(redirect_url)

    active_analysis = analyses.get(active_tab)
    input_data = json.loads(active_analysis.input_data) if active_analysis and active_analysis.input_data else {}
    raw_result = active_analysis.ai_result if active_analysis else None
    # env_analysis는 sub_type별 dict로 저장 — dict이면 그대로, 아니면 None
    if active_tab == 'env_analysis' and raw_result:
        try:
            parsed = json.loads(raw_result)
            ai_result = parsed if isinstance(parsed, dict) else {}
        except Exception:
            ai_result = {}
    else:
        ai_result = raw_result

    from app.services.ai_service import MODULE_FIELDS
    tab_fields = MODULE_FIELDS.get(active_tab, [])

    return render_template('dashboard/project_detail.html',
                           project=project,
                           modules=MODULES,
                           analyses=analyses,
                           is_owner=is_owner,
                           active_tab=active_tab,
                           input_data=input_data,
                           ai_result=ai_result,
                           tab_fields=tab_fields)


@dashboard_bp.route('/projects/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    project = Project.query.filter_by(id=project_id, owner_id=current_user.id).first_or_404()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('프로젝트 이름을 입력해주세요.', 'error')
        else:
            project.name = name
            project.organization = request.form.get('organization', '').strip()
            project.business_manager = request.form.get('business_manager', '').strip()
            project.project_manager = request.form.get('project_manager', '').strip()
            project.description = request.form.get('description', '').strip()
            project.is_public = request.form.get('is_public') == '1'
            db.session.commit()
            flash('프로젝트 정보가 수정되었습니다.', 'success')
            return redirect(url_for('dashboard.project_detail', project_id=project.id))
    return render_template('dashboard/edit_project.html', project=project)


@dashboard_bp.route('/projects/<int:project_id>/toggle_public', methods=['POST'])
@login_required
def toggle_public(project_id):
    project = Project.query.filter_by(id=project_id, owner_id=current_user.id).first_or_404()
    project.is_public = not project.is_public
    db.session.commit()
    state = '공개' if project.is_public else '비공개'
    return jsonify({'ok': True, 'is_public': project.is_public, 'state': state})


@dashboard_bp.route('/projects/<int:project_id>/pdf')
@login_required
def export_full_docx(project_id):
    from app.services.pdf_service import generate_full_report_pdf

    project = Project.query.filter_by(id=project_id).first_or_404()
    if project.owner_id != current_user.id and not project.is_public:
        flash('접근 권한이 없습니다.', 'error')
        return redirect(url_for('dashboard.index'))

    analyses = {a.module_type: a for a in project.analyses}
    modules = [{'key': m['key'], 'name': m['name']} for m in MODULES]
    buf = generate_full_report_pdf(project, modules, analyses)
    ts = datetime.now().strftime('%m%d%H')
    filename = f"{project.name}_비즈니스모델설계_통합보고서_{ts}.pdf"
    return send_file(buf, mimetype='application/pdf',
                     as_attachment=True, download_name=filename)


@dashboard_bp.route('/projects/<int:project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    project = Project.query.filter_by(id=project_id, owner_id=current_user.id).first_or_404()
    db.session.delete(project)
    db.session.commit()
    flash('프로젝트가 삭제되었습니다.', 'success')
    return redirect(url_for('dashboard.index'))


@dashboard_bp.route('/api/health')
@login_required
def api_health():
    """Railway 환경 진단 — API 키·모델 연결 확인"""
    import os
    from flask import current_app
    api_key = current_app.config.get('ANTHROPIC_API_KEY', '')
    key_preview = (api_key[:12] + '...') if len(api_key) > 12 else ('(없음)' if not api_key else api_key)
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model='claude-opus-4-6',
            max_tokens=16,
            messages=[{'role': 'user', 'content': 'ping'}]
        )
        return jsonify({
            'status': 'ok',
            'api_key': key_preview,
            'model_response': msg.content[0].text[:50],
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'api_key': key_preview,
            'error': str(e),
        }), 500
