from flask import Blueprint, request, jsonify
from src.models.hospital import Hospital, Department, db
from geopy.distance import geodesic
import json
import math

hospitals_bp = Blueprint('hospitals', __name__)

def calculate_distance(lat1, lon1, lat2, lon2):
    """计算两点间距离（公里）"""
    try:
        return geodesic((lat1, lon1), (lat2, lon2)).kilometers
    except:
        return float('inf')

def calculate_hospital_score(hospital, departments_match, distance, user_preferences):
    """计算医院综合评分"""
    # 基础评分
    base_score = 0.5
    
    # 医院等级评分
    level_scores = {"三甲": 1.0, "三乙": 0.8, "二甲": 0.6, "二乙": 0.4, "一甲": 0.2}
    level_score = level_scores.get(hospital.level, 0.3)
    
    # 距离评分（距离越近评分越高）
    if distance <= 5:
        distance_score = 1.0
    elif distance <= 10:
        distance_score = 0.8
    elif distance <= 20:
        distance_score = 0.6
    else:
        distance_score = 0.3
    
    # 科室匹配评分
    department_score = min(departments_match / 3.0, 1.0)  # 最多3个匹配科室
    
    # 医院评分
    rating_score = min(hospital.rating / 5.0, 1.0) if hospital.rating else 0.5
    
    # 综合评分
    final_score = (
        base_score * 0.1 +
        level_score * 0.3 +
        distance_score * 0.3 +
        department_score * 0.2 +
        rating_score * 0.1
    )
    
    return round(final_score, 2)

def init_sample_data():
    """初始化示例数据"""
    # 检查是否已有数据
    if Hospital.query.count() > 0:
        return
    
    # 示例医院数据
    sample_hospitals = [
        {
            "name": "北京协和医院",
            "level": "三甲",
            "address": "北京市东城区东单帅府园1号",
            "latitude": 39.9139,
            "longitude": 116.4074,
            "phone": "010-69156114",
            "website": "https://www.pumch.cn",
            "specialties": json.dumps(["内科", "外科", "妇产科", "儿科", "神经内科", "心血管内科"]),
            "rating": 4.8
        },
        {
            "name": "北京大学第一医院",
            "level": "三甲",
            "address": "北京市西城区西什库大街8号",
            "latitude": 39.9289,
            "longitude": 116.3831,
            "phone": "010-83572211",
            "website": "https://www.bddyyy.com.cn",
            "specialties": json.dumps(["内科", "外科", "泌尿外科", "肾内科", "呼吸内科"]),
            "rating": 4.6
        },
        {
            "name": "北京天坛医院",
            "level": "三甲",
            "address": "北京市丰台区南四环西路119号",
            "latitude": 39.8586,
            "longitude": 116.3969,
            "phone": "010-59978114",
            "website": "https://www.bjtth.org",
            "specialties": json.dumps(["神经内科", "神经外科", "急诊科", "内科"]),
            "rating": 4.7
        },
        {
            "name": "上海华山医院",
            "level": "三甲",
            "address": "上海市静安区乌鲁木齐中路12号",
            "latitude": 31.2165,
            "longitude": 121.4365,
            "phone": "021-52889999",
            "website": "https://www.huashan.org.cn",
            "specialties": json.dumps(["神经内科", "皮肤科", "感染科", "内科", "外科"]),
            "rating": 4.9
        },
        {
            "name": "广州中山大学附属第一医院",
            "level": "三甲",
            "address": "广州市越秀区中山二路1号",
            "latitude": 23.1291,
            "longitude": 113.2644,
            "phone": "020-28823388",
            "website": "https://www.gzsums.edu.cn",
            "specialties": json.dumps(["内科", "外科", "肿瘤科", "心血管内科", "消化内科"]),
            "rating": 4.5
        }
    ]
    
    for hospital_data in sample_hospitals:
        hospital = Hospital(**hospital_data)
        db.session.add(hospital)
    
    db.session.commit()
    
    # 添加科室数据
    departments_data = [
        {"hospital_id": 1, "name": "呼吸内科", "description": "诊治呼吸系统疾病"},
        {"hospital_id": 1, "name": "心血管内科", "description": "诊治心血管疾病"},
        {"hospital_id": 1, "name": "消化内科", "description": "诊治消化系统疾病"},
        {"hospital_id": 1, "name": "神经内科", "description": "诊治神经系统疾病"},
        {"hospital_id": 2, "name": "呼吸内科", "description": "诊治呼吸系统疾病"},
        {"hospital_id": 2, "name": "泌尿外科", "description": "诊治泌尿系统疾病"},
        {"hospital_id": 2, "name": "肾内科", "description": "诊治肾脏疾病"},
        {"hospital_id": 3, "name": "神经内科", "description": "诊治神经系统疾病"},
        {"hospital_id": 3, "name": "神经外科", "description": "神经外科手术"},
        {"hospital_id": 3, "name": "急诊科", "description": "急诊医疗服务"},
        {"hospital_id": 4, "name": "神经内科", "description": "诊治神经系统疾病"},
        {"hospital_id": 4, "name": "皮肤科", "description": "诊治皮肤疾病"},
        {"hospital_id": 4, "name": "感染科", "description": "诊治感染性疾病"},
        {"hospital_id": 5, "name": "肿瘤科", "description": "诊治肿瘤疾病"},
        {"hospital_id": 5, "name": "心血管内科", "description": "诊治心血管疾病"},
        {"hospital_id": 5, "name": "消化内科", "description": "诊治消化系统疾病"}
    ]
    
    for dept_data in departments_data:
        department = Department(**dept_data)
        db.session.add(department)
    
    db.session.commit()

@hospitals_bp.route('/hospitals/recommend', methods=['POST'])
def recommend_hospitals():
    """医院推荐API"""
    try:
        # 初始化示例数据
        init_sample_data()
        
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "请提供推荐参数"}), 400
        
        # 获取参数
        analysis_result = data.get('analysis_result', {})
        location = data.get('location', {})
        radius = data.get('radius', 50000)  # 默认50公里
        preferences = data.get('preferences', {})
        
        user_lat = location.get('latitude')
        user_lng = location.get('longitude')
        
        if not user_lat or not user_lng:
            return jsonify({"error": "请提供用户位置信息"}), 400
        
        # 获取推荐科室
        recommended_departments = analysis_result.get('recommended_departments', [])
        
        # 查询所有医院
        hospitals = Hospital.query.all()
        
        recommendations = []
        
        for hospital in hospitals:
            if not hospital.latitude or not hospital.longitude:
                continue
            
            # 计算距离
            distance = calculate_distance(user_lat, user_lng, hospital.latitude, hospital.longitude)
            
            # 距离过滤
            if distance > radius / 1000:  # 转换为公里
                continue
            
            # 计算科室匹配度
            hospital_specialties = json.loads(hospital.specialties) if hospital.specialties else []
            departments_match = len(set(recommended_departments) & set(hospital_specialties))
            
            # 计算综合评分
            score = calculate_hospital_score(hospital, departments_match, distance, preferences)
            
            # 获取匹配的科室
            matched_departments = list(set(recommended_departments) & set(hospital_specialties))
            
            recommendations.append({
                "hospital": hospital.to_dict(),
                "distance": round(distance, 2),
                "score": score,
                "matched_departments": matched_departments,
                "departments_match_count": departments_match
            })
        
        # 按评分排序
        sort_by = preferences.get('sort_by', 'score')
        if sort_by == 'distance':
            recommendations.sort(key=lambda x: x['distance'])
        elif sort_by == 'rating':
            recommendations.sort(key=lambda x: x['hospital']['rating'], reverse=True)
        else:
            recommendations.sort(key=lambda x: x['score'], reverse=True)
        
        return jsonify({
            "success": True,
            "data": {
                "recommendations": recommendations[:10],  # 返回前10个推荐
                "total_count": len(recommendations),
                "search_params": {
                    "location": location,
                    "radius": radius,
                    "recommended_departments": recommended_departments
                }
            }
        })
        
    except Exception as e:
        return jsonify({"error": f"推荐过程中出现错误: {str(e)}"}), 500

@hospitals_bp.route('/hospitals/<int:hospital_id>', methods=['GET'])
def get_hospital_details(hospital_id):
    """获取医院详情"""
    try:
        hospital = Hospital.query.get(hospital_id)
        
        if not hospital:
            return jsonify({"error": "医院不存在"}), 404
        
        # 获取科室信息
        departments = Department.query.filter_by(hospital_id=hospital_id).all()
        
        return jsonify({
            "success": True,
            "data": {
                "hospital": hospital.to_dict(),
                "departments": [dept.to_dict() for dept in departments]
            }
        })
        
    except Exception as e:
        return jsonify({"error": f"获取医院详情时出现错误: {str(e)}"}), 500

@hospitals_bp.route('/hospitals/search', methods=['GET'])
def search_hospitals():
    """搜索医院"""
    try:
        query = request.args.get('q', '')
        city = request.args.get('city', '')
        level = request.args.get('level', '')
        
        hospitals_query = Hospital.query
        
        if query:
            hospitals_query = hospitals_query.filter(Hospital.name.contains(query))
        
        if city:
            hospitals_query = hospitals_query.filter(Hospital.address.contains(city))
        
        if level:
            hospitals_query = hospitals_query.filter(Hospital.level == level)
        
        hospitals = hospitals_query.limit(20).all()
        
        return jsonify({
            "success": True,
            "data": [hospital.to_dict() for hospital in hospitals]
        })
        
    except Exception as e:
        return jsonify({"error": f"搜索医院时出现错误: {str(e)}"}), 500

@hospitals_bp.route('/hospitals/nearby', methods=['POST'])
def get_nearby_hospitals():
    """获取附近医院"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "请提供位置信息"}), 400
        
        user_lat = data.get('latitude')
        user_lng = data.get('longitude')
        radius = data.get('radius', 10000)  # 默认10公里
        
        if not user_lat or not user_lng:
            return jsonify({"error": "请提供有效的位置坐标"}), 400
        
        hospitals = Hospital.query.all()
        nearby_hospitals = []
        
        for hospital in hospitals:
            if not hospital.latitude or not hospital.longitude:
                continue
            
            distance = calculate_distance(user_lat, user_lng, hospital.latitude, hospital.longitude)
            
            if distance <= radius / 1000:  # 转换为公里
                hospital_data = hospital.to_dict()
                hospital_data['distance'] = round(distance, 2)
                nearby_hospitals.append(hospital_data)
        
        # 按距离排序
        nearby_hospitals.sort(key=lambda x: x['distance'])
        
        return jsonify({
            "success": True,
            "data": nearby_hospitals
        })
        
    except Exception as e:
        return jsonify({"error": f"获取附近医院时出现错误: {str(e)}"}), 500

