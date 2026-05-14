// ===== 모듈 설명 토글 =====
function toggleModuleDesc(header) {
    header.classList.toggle('collapsed');
    header.nextElementSibling.classList.toggle('collapsed');
}

// ===== AI 질문 모달 =====
let _askTargetField = null;
let _askFieldLabel = '';

const DEFAULT_QUESTIONS = {
    // PESTEL
    political:     '우리 사업에 영향을 미치는 주요 정치·정책적 환경 요인은 무엇인가요? 관련 규제나 정부 정책 방향도 포함해서 알려주세요.',
    economic:      '현재 경제 환경에서 우리 사업에 영향을 미치는 주요 요인(금리, 환율, 경기 흐름, 소비 트렌드 등)은 무엇인가요?',
    social:        '우리 사업과 관련된 사회·문화적 트렌드 변화(인구구조, 라이프스타일, 소비자 인식 등)는 어떻게 분석할 수 있나요?',
    technology:    '우리 사업에 영향을 주는 기술 혁신 트렌드(디지털 전환, AI, 자동화 등)는 무엇이며 어떻게 대응해야 하나요?',
    environmental: '우리 사업에 관련된 환경 규제, 탄소중립, ESG 요구사항은 무엇이며 어떤 영향을 미치나요?',
    legal:         '우리 사업 운영에 영향을 주는 주요 법규·규제(노동법, 산업 규제, 소비자보호법 등)는 무엇인가요?',

    // 5 Forces
    competitive_rivalry: '현재 우리가 속한 시장의 경쟁 강도는 어느 수준인가요? 주요 경쟁사와 경쟁 방식을 분석해주세요.',
    new_entrants:        '우리 시장에 신규 진입자가 나타날 가능성은 얼마나 되나요? 진입 장벽은 어떻게 평가할 수 있나요?',
    substitutes:         '우리 제품·서비스를 대체할 수 있는 대안은 무엇이 있으며, 고객 전환 가능성은 얼마나 되나요?',
    buyer_power:         '우리 고객(구매자)의 협상력은 어느 수준인가요? 고객 집중도와 가격 민감도를 분석해주세요.',
    supplier_power:      '우리 사업의 주요 공급자 협상력은 어느 수준인가요? 공급망 리스크는 무엇인가요?',

    // SWOT
    strengths:     '우리 사업의 핵심 강점은 무엇인가요? 경쟁사 대비 우위를 가진 역량이나 자산을 정리해주세요.',
    weaknesses:    '우리 사업의 내부 취약점은 무엇인가요? 개선이 필요한 역량이나 자원 부족 영역을 알려주세요.',
    opportunities: '현재 외부 환경에서 우리 사업이 활용할 수 있는 기회 요인은 무엇인가요?',
    threats:       '현재 외부 환경에서 우리 사업에 위협이 되는 요인은 무엇인가요? 리스크 요소를 정리해주세요.',

    // Ansoff
    market_penetration:  '기존 제품으로 기존 시장에서 점유율을 높이기 위한 전략은 무엇인가요? 구체적인 실행 방안을 제안해주세요.',
    product_development: '기존 고객을 대상으로 새로운 제품·서비스를 개발하기 위한 전략과 방향을 제안해주세요.',
    market_development:  '기존 제품으로 새로운 시장(지역, 고객군, 채널)에 진출하기 위한 전략을 제안해주세요.',
    diversification:     '신규 제품으로 신규 시장에 진출하는 다각화 전략을 어떻게 수립해야 하나요? 리스크 관리 방안도 포함해주세요.',

    // 3 Horizons
    horizon1: '현재 핵심 사업의 효율화와 수익성 개선을 위해 단기(0~1년)에 집중해야 할 과제는 무엇인가요?',
    horizon2: '향후 1~3년 내 성장 동력이 될 신사업 영역은 무엇이며, 어떻게 구축해나가야 하나요?',
    horizon3: '3년 이후를 대비한 미래 혁신 아이디어나 파괴적 기술 기회는 무엇인가요?',

    // OGSM
    objectives: '우리 사업의 중장기 비전과 정성적 목표를 어떻게 설정하면 좋을까요? 방향성 있는 표현으로 제안해주세요.',
    goals:      '목표를 달성하기 위한 구체적이고 측정 가능한 수치 목표(매출, 고객 수, 성장률 등)를 어떻게 설정하면 좋을까요?',
    strategies: '목표 달성을 위한 핵심 전략 방향 3~5가지를 제안해주세요.',
    measures:   '전략 실행 여부를 모니터링할 KPI와 측정 지표는 무엇으로 설정하면 좋을까요?',

    // Result Report
    target_vs_actual: '목표 대비 실적 차이(Gap)를 분석할 때 어떤 항목을 중심으로 정리하면 효과적인가요?',
    key_achievements: '이번 기간의 주요 성과를 정리할 때 어떤 관점에서 서술하면 좋을까요?',
    shortfalls:       '목표 미달 항목에 대한 원인을 내부/외부 요인으로 구분하여 분석하는 방법을 알려주세요.',
    external_factors: '우리 사업 성과에 영향을 준 외부 환경 변화(시장, 경쟁, 규제 등)는 어떻게 정리하면 좋을까요?',
};

function openAskModal(fieldName, fieldLabel) {
    _askTargetField = fieldName;
    _askFieldLabel = fieldLabel;
    _lastAnswerText = '';
    document.getElementById('ask-modal-field-name').textContent = fieldLabel + ' — AI 도움받기';
    document.getElementById('ask-question-input').value = DEFAULT_QUESTIONS[fieldName] || '';
    document.getElementById('ask-answer-area').style.display = 'none';
    document.getElementById('ask-action-row').style.display = 'none';
    document.getElementById('ask-btn-text').textContent = '✦ 질문하기';
    document.querySelector('.ask-submit-btn').disabled = false;
    document.getElementById('ask-modal').classList.add('active');
    setTimeout(() => document.getElementById('ask-question-input').focus(), 100);
}

function closeAskModalDirect() {
    document.getElementById('ask-modal').classList.remove('active');
}

function closeAskModal(e) {
    if (e.target.id === 'ask-modal') closeAskModalDirect();
}

// 답변 원문(plain text) 저장용
let _lastAnswerText = '';

function submitAskQuestion() {
    const question = document.getElementById('ask-question-input').value.trim();
    if (!question) return;

    const btn = document.getElementById('ask-btn-text');
    btn.textContent = '분석 중...';
    document.querySelector('.ask-submit-btn').disabled = true;

    const answerArea = document.getElementById('ask-answer-area');
    const answerContent = document.getElementById('ask-answer-content');
    answerArea.style.display = 'block';
    answerContent.innerHTML = '<div class="ask-loading"><div class="ai-loading-orb" style="width:20px;height:20px"></div> <span>Claude AI 답변 생성 중...</span></div>';
    document.getElementById('ask-action-row').style.display = 'none';
    _lastAnswerText = '';

    fetch(`/projects/${projectId}/modules/${moduleType}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, field_label: _askFieldLabel })
    })
    .then(r => r.json())
    .then(data => {
        btn.textContent = '✦ 다시 질문하기';
        document.querySelector('.ask-submit-btn').disabled = false;

        if (data.error) {
            answerContent.innerHTML = `<div class="flash flash-error">${data.error}</div>`;
            return;
        }

        // "--- 입력 제안 ---" 구분선이 있으면 제안 부분을 plain text로, 없으면 전체를 사용
        const raw = data.result;
        const sepIdx = raw.indexOf('--- 입력 제안 ---');
        const displayText = sepIdx !== -1 ? raw.substring(0, sepIdx).trim() : raw.trim();
        const suggText   = sepIdx !== -1 ? raw.substring(sepIdx + 16).trim() : raw.trim();

        _lastAnswerText = suggText;

        answerContent.innerHTML = `<div class="ask-answer-text">${inlineMarkdown(displayText).replace(/\n/g, '<br>')}</div>`;
        document.getElementById('ask-action-row').style.display = 'flex';
        document.getElementById('copy-btn-text').textContent = '📋 전체 복사';
    })
    .catch(() => {
        btn.textContent = '✦ 질문하기';
        document.querySelector('.ask-submit-btn').disabled = false;
        answerContent.innerHTML = '<div class="flash flash-error">요청 중 오류가 발생했습니다.</div>';
    });
}

function copyAnswerText() {
    const text = _lastAnswerText || document.getElementById('ask-answer-content').innerText;
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
        const btn = document.getElementById('copy-btn-text');
        btn.textContent = '✓ 복사됨';
        setTimeout(() => { btn.textContent = '📋 전체 복사'; }, 2000);
    }).catch(() => {
        const range = document.createRange();
        range.selectNodeContents(document.getElementById('ask-answer-content'));
        window.getSelection().removeAllRanges();
        window.getSelection().addRange(range);
        document.execCommand('copy');
        window.getSelection().removeAllRanges();
        const btn = document.getElementById('copy-btn-text');
        btn.textContent = '✓ 복사됨';
        setTimeout(() => { btn.textContent = '📋 전체 복사'; }, 2000);
    });
}

function applyAnswerText() {
    const text = _lastAnswerText;
    if (!text || !_askTargetField) return;
    const target = document.getElementById('field-' + _askTargetField);
    if (target) {
        const existing = target.value.trim();
        target.value = existing ? existing + '\n' + text : text;
        target.focus();
    }
    closeAskModalDirect();
}

// Enter 키로 질문 제출 (Shift+Enter는 줄바꿈)
document.addEventListener('DOMContentLoaded', () => {
    const qInput = document.getElementById('ask-question-input');
    if (qInput) {
        qInput.addEventListener('keydown', e => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submitAskQuestion(); }
        });
    }
});

// ===== AI 전체 자동 입력 모달 =====
// _envAutoFname: env 패널에서 openEnvAskAllModal이 설정, null이면 전체 필드 채움
let _envAutoFname = null;

function openAskAllModal() {
    _envAutoFname = null;
    document.getElementById('ask-all-question-input').value = '';
    document.getElementById('ask-all-status').style.display = 'none';
    document.getElementById('ask-all-result').style.display = 'none';
    document.getElementById('ask-all-btn-text').textContent = '✦ AI 자동 입력 시작';
    document.querySelector('#ask-all-modal .ask-submit-btn').disabled = false;
    document.getElementById('ask-all-modal').classList.add('active');
    setTimeout(() => document.getElementById('ask-all-question-input').focus(), 100);
}

function closeAskAllModalDirect() {
    document.getElementById('ask-all-modal').classList.remove('active');
    _envAutoFname = null;
}

function closeAskAllModal(e) {
    if (e.target.id === 'ask-all-modal') closeAskAllModalDirect();
}

function submitAskAllFields() {
    const extra = document.getElementById('ask-all-question-input').value.trim();

    // 프로젝트 정보를 질문에 자동 포함
    const projectInfoEl = document.querySelector('.ask-all-project-info');
    let projectContext = '';
    if (projectInfoEl) {
        projectInfoEl.querySelectorAll('.ask-all-project-info-item').forEach(item => {
            const key = item.querySelector('.ask-all-info-key')?.textContent || '';
            const val = item.querySelector('.ask-all-info-val')?.textContent || '';
            if (val.trim()) projectContext += `${key}: ${val.trim()}\n`;
        });
    }
    const question = projectContext + (extra ? `\n추가 상황: ${extra}` : '');

    const btn = document.getElementById('ask-all-btn-text');
    btn.textContent = '입력 중...';
    document.querySelector('#ask-all-modal .ask-submit-btn').disabled = true;

    document.getElementById('ask-all-status').style.display = 'block';
    document.getElementById('ask-all-result').style.display = 'none';

    // env 서브모듈 단일 필드 자동 입력 시 single_field 전송
    const body = { question };
    if (_envAutoFname) body.single_field = _envAutoFname;

    fetch(`/projects/${projectId}/modules/${moduleType}/ask-all`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    })
    .then(r => r.json())
    .then(data => {
        document.getElementById('ask-all-status').style.display = 'none';
        btn.textContent = '✦ 다시 입력';
        document.querySelector('#ask-all-modal .ask-submit-btn').disabled = false;

        if (data.error) {
            document.getElementById('ask-all-status').style.display = 'block';
            document.getElementById('ask-all-status').innerHTML =
                `<div class="flash flash-error">${data.error}</div>`;
            return;
        }

        // 각 필드에 값 채우기
        // _envAutoFname 이 설정된 경우 해당 단일 필드만 채움 (env 패널 자동 입력)
        const resultList = document.getElementById('ask-all-result-list');
        resultList.innerHTML = '';

        const targetFields = _envAutoFname ? [_envAutoFname] : (moduleFields || []);
        targetFields.forEach(fname => {
            // 해당 필드명으로 매핑된 값이 없으면 응답의 첫 번째 키 값을 사용 (env 단일 필드)
            const val = data[fname] ?? (_envAutoFname ? Object.values(data)[0] : null);
            if (!val) return;
            const el = document.getElementById('field-' + fname);
            if (el) el.value = val;
            const item = document.createElement('div');
            item.className = 'ask-all-result-item';
            item.innerHTML = `<p>${val.replace(/\n/g, '<br>')}</p>`;
            resultList.appendChild(item);
        });

        document.getElementById('ask-all-result').style.display = 'block';
    })
    .catch(() => {
        document.getElementById('ask-all-status').style.display = 'none';
        btn.textContent = '✦ AI 자동 입력 시작';
        document.querySelector('#ask-all-modal .ask-submit-btn').disabled = false;
        document.getElementById('ask-all-status').style.display = 'block';
        document.getElementById('ask-all-status').innerHTML =
            '<div class="flash flash-error">요청 중 오류가 발생했습니다.</div>';
    });
}

// Enter 키로 ask-all 질문 제출
document.addEventListener('DOMContentLoaded', () => {
    const allInput = document.getElementById('ask-all-question-input');
    if (allInput) {
        allInput.addEventListener('keydown', e => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submitAskAllFields(); }
        });
    }
    const analyzeInput = document.getElementById('analyze-extra-input');
    if (analyzeInput) {
        analyzeInput.addEventListener('keydown', e => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submitAnalysis(); }
        });
    }
});

// ===== 사이드바 수행 조직 토글 =====
function toggleOrg(header) {
    header.classList.toggle('collapsed');
    const projects = header.nextElementSibling;
    projects.classList.toggle('collapsed');
}

// ===== 사이드바 프로젝트 상세 토글 =====
function toggleProjectDetail(row) {
    const detail = row.nextElementSibling;
    const isOpen = detail.classList.contains('open');
    detail.classList.toggle('open', !isOpen);
    row.classList.toggle('detail-open', !isOpen);
}

// ===== AI 분석 모달 =====
function runAnalysis() {
    const input = document.getElementById('analyze-extra-input');
    if (input) input.value = '';
    // 프리셋 선택 초기화
    document.querySelectorAll('.analyze-preset-btn').forEach(b => b.classList.remove('active'));
    const defaultBtn = document.querySelector('.analyze-preset-btn[data-text=""]');
    if (defaultBtn) defaultBtn.classList.add('active');

    document.getElementById('analyze-run-btn').disabled = false;
    document.getElementById('analyze-btn-text').textContent = '🤖 AI 분석 시작';
    document.getElementById('analyze-modal').classList.add('active');
    setTimeout(() => { if (input) input.focus(); }, 100);
}

function closeAnalyzeModalDirect() {
    document.getElementById('analyze-modal').classList.remove('active');
}

function closeAnalyzeModal(e) {
    if (e.target.id === 'analyze-modal') closeAnalyzeModalDirect();
}

function setAnalyzePreset(btn) {
    document.querySelectorAll('.analyze-preset-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('analyze-extra-input').value = btn.dataset.text;
}

function submitAnalysis() {
    const extraPrompt = (document.getElementById('analyze-extra-input')?.value || '').trim();
    const resultDiv = document.getElementById('ai-result');
    if (!resultDiv) return;

    closeAnalyzeModalDirect();

    document.getElementById('analyze-run-btn').disabled = true;
    document.getElementById('analyze-btn-text').textContent = '분석 중...';

    resultDiv.innerHTML = `
        <div class="ai-loading">
            <div class="ai-loading-orb"></div>
            <div class="ai-loading-text">
                <span>Claude AI 분석 중</span>
                <span class="ai-loading-dots"><span>.</span><span>.</span><span>.</span></span>
            </div>
        </div>`;

    fetch(`/projects/${projectId}/modules/${moduleType}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ extra_prompt: extraPrompt }),
    })
    .then(res => res.text().then(text => {
        try { return { ok: res.ok, status: res.status, data: JSON.parse(text) }; }
        catch { return { ok: res.ok, status: res.status, data: { error: `서버 응답 파싱 실패 (HTTP ${res.status}): ${text.slice(0, 200)}` } }; }
    }))
    .then(({ ok, status, data }) => {
        document.getElementById('analyze-run-btn').disabled = false;
        document.getElementById('analyze-btn-text').textContent = '🤖 AI 분석 시작';
        if (data.error) {
            resultDiv.innerHTML = `<div class="flash flash-error"><strong>오류 (HTTP ${status}):</strong> ${data.error}</div>`;
        } else {
            resultDiv.innerHTML = renderAIResult(data.result, moduleType);
        }
    })
    .catch(err => {
        document.getElementById('analyze-run-btn').disabled = false;
        document.getElementById('analyze-btn-text').textContent = '🤖 AI 분석 시작';
        resultDiv.innerHTML = `<div class="flash flash-error">네트워크 오류: ${err.message || err}</div>`;
    });
}

// runSubAnalysis / runAllSubAnalysis / switchEnvFull / openEnvAskAllModal / ENV_SUB_TYPES
// are defined inline in project_detail.html for env_analysis tab (they use Jinja2 context)

// ===== AI 결과 렌더러 (BCG HTML 직접 출력) =====
function renderAIResult(text, moduleType) {
    const meta = getModuleMeta(moduleType);
    return `
    <div class="ai-result-visual">
        <div class="ai-result-topbar">
            <div class="ai-result-topbar-left">
                <span class="ai-result-icon">${meta.icon}</span>
                <div>
                    <div class="ai-result-title">${meta.title} — BCG Style 분석 완료</div>
                    <div class="ai-result-timestamp">분석 시각: ${new Date().toLocaleString('ko-KR')}</div>
                </div>
            </div>
            <span class="model-badge-v2">✦ Claude AI</span>
        </div>
        <div class="bcg-report">${text}</div>
    </div>`;
}

// ===== 유틸 함수 =====
function getModuleMeta(type) {
    const map = {
        biz_definition: { icon: '🎯', title: '사업 정의' },
        env_analysis:   { icon: '🌐', title: '환경 분석' },
        value_design:   { icon: '💡', title: '가치 설계' },
        revenue_model:  { icon: '💰', title: '수익 구조' },
        execution:      { icon: '🚀', title: '실행 체계' },
        validation:     { icon: '🔬', title: '검증·정제' },
    };
    return map[type] || { icon: '✦', title: 'AI 분석' };
}

// ===== 인라인 마크다운 변환 (최소) =====
function inlineMarkdown(text) {
    return text
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/`(.+?)`/g, '<code>$1</code>');
}

// ===== 모듈 패널 리사이저 =====
document.addEventListener('DOMContentLoaded', () => {
    const resizer = document.querySelector('.module-resizer');
    if (!resizer) return;

    const layout      = resizer.closest('.module-layout');
    const inputPanel  = layout.querySelector('.input-panel');
    const resultPanel = layout.querySelector('.result-panel');
    const STORAGE_KEY = 'module_panel_ratio';

    function applyRatio(ratio) {
        // flex 속성을 먼저 해제해야 offsetWidth가 정확히 계산됨
        inputPanel.style.flex   = 'none';
        resultPanel.style.flex  = 'none';
        const total = layout.offsetWidth - resizer.offsetWidth - 8;
        if (total <= 0) return;
        inputPanel.style.width  = (total * ratio) + 'px';
        resultPanel.style.width = (total * (1 - ratio)) + 'px';
    }

    // 렌더링 완료 후 비율 적용 (2프레임 대기로 레이아웃 확정 후 실행)
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            const saved = parseFloat(localStorage.getItem(STORAGE_KEY));
            applyRatio(!isNaN(saved) && saved > 0.1 && saved < 0.9 ? saved : 0.5);
        });
    });

    let startX, startInputW, startResultW;

    resizer.addEventListener('mousedown', e => {
        e.preventDefault();
        startX       = e.clientX;
        startInputW  = inputPanel.offsetWidth;
        startResultW = resultPanel.offsetWidth;
        resizer.classList.add('dragging');
        document.body.style.cursor     = 'col-resize';
        document.body.style.userSelect = 'none';
    });

    document.addEventListener('mousemove', e => {
        if (!resizer.classList.contains('dragging')) return;
        const dx        = e.clientX - startX;
        const total     = startInputW + startResultW;
        const newInputW = Math.max(200, Math.min(total - 200, startInputW + dx));
        inputPanel.style.width  = newInputW + 'px';
        resultPanel.style.width = (total - newInputW) + 'px';
    });

    document.addEventListener('mouseup', () => {
        if (!resizer.classList.contains('dragging')) return;
        resizer.classList.remove('dragging');
        document.body.style.cursor     = '';
        document.body.style.userSelect = '';
        const total = inputPanel.offsetWidth + resultPanel.offsetWidth;
        localStorage.setItem(STORAGE_KEY, (inputPanel.offsetWidth / total).toFixed(4));
    });

    // 더블클릭 → 50:50 리셋
    resizer.addEventListener('dblclick', () => {
        localStorage.setItem(STORAGE_KEY, '0.5');
        applyRatio(0.5);
    });

    // 창 크기 변경 시 비율 유지
    window.addEventListener('resize', () => {
        const saved = parseFloat(localStorage.getItem(STORAGE_KEY)) || 0.5;
        applyRatio(saved);
    });
});

// ===== 사이드바 리사이저 =====
document.addEventListener('DOMContentLoaded', () => {
    const resizer = document.getElementById('sidebar-resizer');
    if (!resizer) return;

    const sidebar = document.querySelector('.sidebar');
    const STORAGE_KEY = 'sidebar_width';
    const DEFAULT_W  = 220;
    const MIN_W      = 140;
    const MAX_W      = 480;

    function applyWidth(w) {
        const clamped = Math.max(MIN_W, Math.min(MAX_W, w));
        sidebar.style.width = clamped + 'px';
    }

    const saved = parseInt(localStorage.getItem(STORAGE_KEY));
    applyWidth(!isNaN(saved) ? saved : DEFAULT_W);

    let startX, startW;

    resizer.addEventListener('mousedown', e => {
        e.preventDefault();
        startX = e.clientX;
        startW = sidebar.offsetWidth;
        resizer.classList.add('dragging');
        document.body.style.cursor     = 'col-resize';
        document.body.style.userSelect = 'none';
    });

    document.addEventListener('mousemove', e => {
        if (!resizer.classList.contains('dragging')) return;
        applyWidth(startW + (e.clientX - startX));
    });

    document.addEventListener('mouseup', () => {
        if (!resizer.classList.contains('dragging')) return;
        resizer.classList.remove('dragging');
        document.body.style.cursor     = '';
        document.body.style.userSelect = '';
        localStorage.setItem(STORAGE_KEY, sidebar.offsetWidth);
    });

    resizer.addEventListener('dblclick', () => {
        applyWidth(DEFAULT_W);
        localStorage.setItem(STORAGE_KEY, DEFAULT_W);
    });
});

// ===== env-col-resizer 드래그 (env-full-wrap 레이아웃) =====
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.env-col-resizer').forEach(resizer => {
        const panel    = resizer.closest('.env-full-panel');
        if (!panel) return;
        const inputCol  = panel.querySelector('.env-input-col');
        const resultCol = panel.querySelector('.env-result-col');
        const key       = resizer.dataset.key || 'default';
        const STORAGE_KEY = 'env_panel_ratio_' + key;

        function applyRatio(ratio) {
            const total = panel.offsetWidth - resizer.offsetWidth;
            if (total <= 0) return;
            inputCol.style.flex  = 'none';
            resultCol.style.flex = 'none';
            inputCol.style.width  = (total * ratio) + 'px';
            resultCol.style.width = (total * (1 - ratio)) + 'px';
        }

        requestAnimationFrame(() => requestAnimationFrame(() => {
            const saved = parseFloat(localStorage.getItem(STORAGE_KEY));
            applyRatio(!isNaN(saved) && saved > 0.1 && saved < 0.9 ? saved : 0.42);
        }));

        let startX, startInputW, startResultW;

        resizer.addEventListener('mousedown', e => {
            e.preventDefault();
            startX       = e.clientX;
            startInputW  = inputCol.offsetWidth;
            startResultW = resultCol.offsetWidth;
            resizer.classList.add('dragging');
            document.body.style.cursor     = 'col-resize';
            document.body.style.userSelect = 'none';
        });

        document.addEventListener('mousemove', e => {
            if (!resizer.classList.contains('dragging')) return;
            const dx       = e.clientX - startX;
            const total    = startInputW + startResultW;
            const newInputW = Math.max(180, Math.min(total - 180, startInputW + dx));
            inputCol.style.width  = newInputW + 'px';
            resultCol.style.width = (total - newInputW) + 'px';
        });

        document.addEventListener('mouseup', () => {
            if (!resizer.classList.contains('dragging')) return;
            resizer.classList.remove('dragging');
            document.body.style.cursor     = '';
            document.body.style.userSelect = '';
            const total = inputCol.offsetWidth + resultCol.offsetWidth;
            localStorage.setItem(STORAGE_KEY, (inputCol.offsetWidth / total).toFixed(4));
        });

        resizer.addEventListener('dblclick', () => {
            localStorage.setItem(STORAGE_KEY, '0.42');
            applyRatio(0.42);
        });
    });

    window.addEventListener('resize', () => {
        document.querySelectorAll('.env-col-resizer').forEach(resizer => {
            const panel = resizer.closest('.env-full-panel');
            if (!panel) return;
            const inputCol = panel.querySelector('.env-input-col');
            const key = resizer.dataset.key || 'default';
            const saved = parseFloat(localStorage.getItem('env_panel_ratio_' + key)) || 0.42;
            const total = panel.offsetWidth - resizer.offsetWidth;
            if (total <= 0) return;
            inputCol.style.width  = (total * saved) + 'px';
            const resultCol = panel.querySelector('.env-result-col');
            if (resultCol) resultCol.style.width = (total * (1 - saved)) + 'px';
        });
    });
});

// ===== 플래시 메시지 자동 숨김 =====
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        document.querySelectorAll('.flash').forEach(el => {
            el.style.transition = 'opacity 0.5s';
            el.style.opacity = '0';
            setTimeout(() => el.remove(), 500);
        });
    }, 3000);
});
