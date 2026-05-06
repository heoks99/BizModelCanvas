from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_required, current_user
from app import db
from app.models.project import Project, Analysis
from app.services.ai_service import analyze_with_claude
import json

modules_bp = Blueprint('modules', __name__, url_prefix='/projects/<int:project_id>/modules')

def get_project_or_404(project_id):
    return Project.query.filter_by(id=project_id, owner_id=current_user.id).first_or_404()

def get_or_create_analysis(project_id, module_type):
    analysis = Analysis.query.filter_by(project_id=project_id, module_type=module_type).first()
    if not analysis:
        analysis = Analysis(project_id=project_id, module_type=module_type)
        db.session.add(analysis)
    return analysis

@modules_bp.route('/<module_type>', methods=['GET', 'POST'])
@login_required
def module_view(project_id, module_type):
    project = get_project_or_404(project_id)
    analysis = Analysis.query.filter_by(project_id=project_id, module_type=module_type).first()
    input_data = json.loads(analysis.input_data) if analysis and analysis.input_data else {}
    ai_result = analysis.ai_result if analysis else None

    if request.method == 'POST':
        form_data = request.form.to_dict()
        analysis = get_or_create_analysis(project_id, module_type)
        analysis.input_data = json.dumps(form_data, ensure_ascii=False)
        db.session.commit()
        flash('데이터가 저장되었습니다.', 'success')
        return redirect(url_for('modules.module_view', project_id=project_id, module_type=module_type))

    template_map = {
        'biz_definition': 'modules/biz_definition.html',
        'env_analysis':   'modules/env_analysis.html',
        'value_design':   'modules/value_design.html',
        'revenue_model':  'modules/revenue_model.html',
        'execution':      'modules/execution.html',
        'validation':     'modules/validation.html',
    }
    template = template_map.get(module_type)
    if not template:
        flash('존재하지 않는 모듈입니다.', 'error')
        return redirect(url_for('dashboard.project_detail', project_id=project_id))

    analyses = {a.module_type: a for a in project.analyses}
    return render_template(template, project=project, input_data=input_data, ai_result=ai_result, module_type=module_type, analyses=analyses)

@modules_bp.route('/<module_type>/analyze', methods=['POST'])
@login_required
def analyze(project_id, module_type):
    project = get_project_or_404(project_id)
    analysis = Analysis.query.filter_by(project_id=project_id, module_type=module_type).first()

    if not analysis or not analysis.input_data:
        return jsonify({'error': '먼저 데이터를 입력하고 저장해주세요.'}), 400

    input_data = json.loads(analysis.input_data)
    data = request.get_json(silent=True) or {}
    extra_prompt = data.get('extra_prompt', '').strip()
    sub_type = data.get('sub_type', '').strip()

    try:
        result = analyze_with_claude(module_type, input_data, project.name, project.organization, extra_prompt, sub_type)
    except Exception as e:
        return jsonify({'error': f'AI 분석 중 오류가 발생했습니다: {str(e)}'}), 500

    # AI 서비스가 에러 HTML을 반환한 경우 JSON error로 전환
    if result.startswith('<div class="bcg-insight-warn"><strong>AI 분석 오류'):
        import re as _re
        msg = _re.sub(r'<[^>]+>', '', result).strip()
        return jsonify({'error': msg}), 500

    # env_analysis: sub_type별 결과를 JSON 딕셔너리에 부분 저장
    if module_type == 'env_analysis' and sub_type:
        existing = {}
        if analysis.ai_result:
            try:
                existing = json.loads(analysis.ai_result)
                if not isinstance(existing, dict):
                    existing = {}
            except Exception:
                existing = {}
        existing[sub_type] = result
        analysis.ai_result = json.dumps(existing, ensure_ascii=False)
    else:
        analysis.ai_result = result

    db.session.commit()
    return jsonify({'result': result})


@modules_bp.route('/<module_type>/ask', methods=['POST'])
@login_required
def ask_field(project_id, module_type):
    project = get_project_or_404(project_id)
    data = request.get_json()
    question = (data or {}).get('question', '').strip()
    field_label = (data or {}).get('field_label', '')

    if not question:
        return jsonify({'error': '질문을 입력해주세요.'}), 400

    from app.services.ai_service import ask_field_with_claude
    result = ask_field_with_claude(
        module_type=module_type,
        field_label=field_label,
        question=question,
        project_name=project.name,
        organization=project.organization or ''
    )
    return jsonify({'result': result})


@modules_bp.route('/<module_type>/ask-all', methods=['POST'])
@login_required
def ask_all_fields(project_id, module_type):
    project = get_project_or_404(project_id)
    data = request.get_json()
    question = (data or {}).get('question', '').strip()
    if not question:
        return jsonify({'error': '질문을 입력해주세요.'}), 400

    from app.services.ai_service import ask_all_fields_with_claude
    result = ask_all_fields_with_claude(
        module_type=module_type,
        question=question,
        project_name=project.name,
        organization=project.organization or ''
    )
    return jsonify(result)


@modules_bp.route('/<module_type>/pdf')
@login_required
def export_module_docx(project_id, module_type):
    project = get_project_or_404(project_id)
    analysis = Analysis.query.filter_by(project_id=project_id, module_type=module_type).first()
    ai_result = analysis.ai_result if analysis else None

    from app.services.pdf_service import generate_module_pdf, MODULE_META
    MODULE_STEP = {
        'biz_definition': '01',
        'env_analysis':   '02',
        'value_design':   '03',
        'revenue_model':  '04',
        'execution':      '05',
        'validation':     '06',
    }
    buf = generate_module_pdf(project, module_type, ai_result)
    module_name = MODULE_META.get(module_type, {}).get('name', module_type)
    step = MODULE_STEP.get(module_type, '00')
    filename = f"{project.name}_Step{step}_{module_name}.pdf"
    return send_file(buf, mimetype='application/pdf',
                     as_attachment=True, download_name=filename)
