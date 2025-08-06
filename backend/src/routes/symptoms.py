from flask import Blueprint, request, jsonify
import json
import re

symptoms_bp = Blueprint('symptoms', __name__)

# 简化的症状-疾病知识库
SYMPTOM_DISEASE_MAP = {
    "发热": {
        "diseases": ["感冒", "流感", "肺炎", "扁桃体炎"],
        "departments": ["内科", "呼吸内科", "感染科"],
        "severity_weight": 0.8
    },
    "咳嗽": {
        "diseases": ["感冒", "支气管炎", "肺炎", "哮喘"],
        "departments": ["呼吸内科", "内科"],
        "severity_weight": 0.6
    },
    "头痛": {
        "diseases": ["感冒", "偏头痛", "高血压", "脑炎"],
        "departments": ["神经内科", "内科"],
        "severity_weight": 0.7
    },
    "腹痛": {
        "diseases": ["胃炎", "阑尾炎", "肠胃炎", "胆囊炎"],
        "departments": ["消化内科", "普外科", "内科"],
        "severity_weight": 0.9
    },
    "胸痛": {
        "diseases": ["心绞痛", "肺炎", "胸膜炎", "心肌梗死"],
        "departments": ["心血管内科", "呼吸内科", "急诊科"],
        "severity_weight": 0.95
    },
    "恶心": {
        "diseases": ["胃炎", "食物中毒", "妊娠反应", "脑震荡"],
        "departments": ["消化内科", "内科", "妇产科"],
        "severity_weight": 0.5
    },
    "呕吐": {
        "diseases": ["胃炎", "食物中毒", "肠胃炎", "脑炎"],
        "departments": ["消化内科", "内科", "神经内科"],
        "severity_weight": 0.7
    },
    "腹泻": {
        "diseases": ["肠胃炎", "食物中毒", "肠炎", "痢疾"],
        "departments": ["消化内科", "内科", "感染科"],
        "severity_weight": 0.6
    },
    "乏力": {
        "diseases": ["感冒", "贫血", "甲状腺功能减退", "糖尿病"],
        "departments": ["内科", "内分泌科", "血液科"],
        "severity_weight": 0.4
    },
    "失眠": {
        "diseases": ["焦虑症", "抑郁症", "甲状腺功能亢进", "更年期综合征"],
        "departments": ["精神科", "内分泌科", "神经内科"],
        "severity_weight": 0.3
    }
}

def normalize_symptoms(symptom_text):
    """标准化症状描述"""
    # 简单的关键词匹配，不使用jieba
    symptoms = []
    
    # 直接在文本中查找症状关键词
    for symptom in SYMPTOM_DISEASE_MAP.keys():
        if symptom in symptom_text:
            symptoms.append(symptom)
    
    return list(set(symptoms))  # 去重

def calculate_severity_score(severity, duration):
    """计算严重程度评分"""
    severity_scores = {"轻微": 0.3, "中等": 0.6, "严重": 0.9}
    duration_scores = {"几小时": 0.2, "1-2天": 0.4, "3-7天": 0.7, "超过一周": 1.0}
    
    severity_score = severity_scores.get(severity, 0.5)
    duration_score = duration_scores.get(duration, 0.5)
    
    return (severity_score + duration_score) / 2

def analyze_symptoms_logic(symptoms, severity="中等", duration="1-2天", additional_info=""):
    """症状分析核心逻辑"""
    normalized_symptoms = normalize_symptoms(" ".join(symptoms) + " " + additional_info)
    
    if not normalized_symptoms:
        return {
            "error": "未能识别有效症状，请重新描述",
            "suggestions": ["请使用更具体的症状描述", "如：发热、咳嗽、头痛等"]
        }
    
    # 收集可能的疾病和科室
    possible_diseases = {}
    recommended_departments = set()
    
    severity_score = calculate_severity_score(severity, duration)
    
    for symptom in normalized_symptoms:
        if symptom in SYMPTOM_DISEASE_MAP:
            symptom_data = SYMPTOM_DISEASE_MAP[symptom]
            weight = symptom_data["severity_weight"] * severity_score
            
            # 累积疾病评分
            for disease in symptom_data["diseases"]:
                if disease not in possible_diseases:
                    possible_diseases[disease] = 0
                possible_diseases[disease] += weight
            
            # 收集推荐科室
            recommended_departments.update(symptom_data["departments"])
    
    # 排序疾病
    sorted_diseases = sorted(possible_diseases.items(), key=lambda x: x[1], reverse=True)
    
    # 生成建议
    urgency_level = "低"
    if severity_score > 0.8:
        urgency_level = "高"
    elif severity_score > 0.5:
        urgency_level = "中"
    
    return {
        "normalized_symptoms": normalized_symptoms,
        "possible_diseases": [{"name": disease, "confidence": round(score, 2)} for disease, score in sorted_diseases[:5]],
        "recommended_departments": list(recommended_departments),
        "urgency_level": urgency_level,
        "severity_score": round(severity_score, 2),
        "advice": generate_advice(normalized_symptoms, urgency_level)
    }

def generate_advice(symptoms, urgency_level):
    """生成医疗建议"""
    advice = []
    
    if urgency_level == "高":
        advice.append("建议立即就医，症状较为严重")
        advice.append("如有紧急情况请拨打120急救电话")
    elif urgency_level == "中":
        advice.append("建议尽快就医，避免症状加重")
        advice.append("注意休息，多喝水")
    else:
        advice.append("可以先观察症状变化")
        advice.append("注意休息，保持良好作息")
    
    # 针对特定症状的建议
    if "发热" in symptoms:
        advice.append("注意体温监测，适当降温")
    if "咳嗽" in symptoms:
        advice.append("避免刺激性食物，保持室内湿度")
    if "腹痛" in symptoms:
        advice.append("避免进食刺激性食物，注意腹部保暖")
    
    return advice

@symptoms_bp.route('/symptoms/analyze', methods=['POST'])
def analyze_symptoms():
    """症状分析API"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "请提供症状信息"}), 400
        
        symptoms = data.get('symptoms', [])
        severity = data.get('severity', '中等')
        duration = data.get('duration', '1-2天')
        additional_info = data.get('additional_info', '')
        
        if not symptoms:
            return jsonify({"error": "请提供至少一个症状"}), 400
        
        # 执行症状分析
        result = analyze_symptoms_logic(symptoms, severity, duration, additional_info)
        
        return jsonify({
            "success": True,
            "data": result
        })
        
    except Exception as e:
        return jsonify({"error": f"分析过程中出现错误: {str(e)}"}), 500

@symptoms_bp.route('/symptoms/suggestions', methods=['GET'])
def get_symptom_suggestions():
    """获取症状建议列表"""
    try:
        query = request.args.get('q', '').lower()
        
        suggestions = []
        for symptom in SYMPTOM_DISEASE_MAP.keys():
            if not query or query in symptom:
                suggestions.append({
                    "name": symptom,
                    "category": "常见症状"
                })
        
        return jsonify({
            "success": True,
            "data": suggestions[:10]  # 限制返回数量
        })
        
    except Exception as e:
        return jsonify({"error": f"获取建议时出现错误: {str(e)}"}), 500

