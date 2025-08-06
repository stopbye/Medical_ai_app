print("DEBUG: ai_assistant.py loaded successfully.")

import os
from flask import Blueprint, request, jsonify
import json
import requests
from dashscope import Generation
import codecs # 临时导入，用于处理BOM

# 以下导入是 Qwen-Agent 工具体系的基础概念，尽管为了解决Flask热重载问题，
# 我们不再直接依赖其注册机制，而是手动处理工具实例化和调用。
# from qwen_agent.tools.base import BaseTool # 示例导入，已移除直接继承

ai_bp = Blueprint('ai_assistant', __name__)

DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY")

# --- AmapWeather 工具类定义 ---
# 这个类定义了一个可被AI助手调用的高德天气查询工具。
# 它的设计目标是封装对高德天气API的调用逻辑。
# 为了解决Flask开发模式下（特别是热重载）工具被重复注册的问题，
# 我们采取直接定义类属性和方法的方式，不依赖 Qwen-Agent 的 `@register_tool` 装饰器。
class AmapWeather:
    # 工具名称：AI模型将使用此名称来识别并调用该工具。
    # 必须与 DashScope 模型配置中工具的 'name' 字段完全一致。
    name = 'amap_weather'
    # 工具描述：向AI模型解释该工具的功能和用途。
    # 清晰、准确的描述有助于模型正确理解何时调用此工具。
    description = '获取对应城市或区县的实时天气数据。请提供具体到区或县的名称，例如"海淀区"、"锦江区"等，而不是笼统的城市名。'
    # 工具参数：定义工具所需的输入参数及其类型和描述。
    # 这些参数会转化为模型的 `parameters` JSON Schema。
    parameters = [{
        'name': 'location', # 参数名称
        'type': 'string',    # 参数类型
        'description': '城市/区具体名称，如`北京市海淀区`请描述为`海淀区`', # 参数描述，指导模型如何提供值
        'required': True     # 标记此参数为必需
    }]

    # 构造函数：用于初始化工具实例。
    # cfg: 可选配置字典，用于传入API Key等。
    def __init__(self, cfg=None):
        self.cfg = cfg if cfg is not None else {}
        # 高德天气API的基础URL，其中包含占位符 {city} 和 {key}。
        self.url = 'https://restapi.amap.com/v3/weather/weatherInfo?city={city}&key={key}'
        # 导入 pandas：用于读取和处理城市编码数据。
        # 这里确保 pandas 在运行时可用。
        import pandas as pd
        try:
            # 尝试从阿里云OSS下载高德行政区划编码表。
            # 这个Excel文件包含了城市名称和对应的adcode，用于精确查询。
            self.city_df = pd.read_excel('https://modelscope.oss-cn-beijing.aliyuncs.com/resource/agent/AMap_adcode_citycode.xlsx')
        except Exception as e:
            # 如果下载或加载失败，打印错误信息，并回退到一个空的DataFrame，以防止程序崩溃。
            print(f"Error loading city data: {e}. Please ensure you have internet access and pandas is installed correctly.")
            self.city_df = pd.DataFrame(columns=['中文名', 'adcode']) # Fallback to empty DataFrame

        # 获取高德API Key：优先从cfg中获取，其次从环境变量WEATHER_API中获取。
        # 这是一个关键的安全措施，避免将API Key硬编码。
        self.token = self.cfg.get('token', os.environ.get('WEATHER_API', ''))
        if not self.token:
            print("Warning: WEATHER_API environment variable not set. AmapWeather tool may not function.")

    # 辅助方法：根据城市名称获取其高德行政区划代码 (adcode)。
    # adcode对于精确天气查询至关重要。
    def get_city_adcode(self, city_name):
        # 在城市DataFrame中过滤，查找匹配中文名的行。
        filtered_df = self.city_df[self.city_df['中文名'] == city_name]
        if filtered_df.empty:
            # 如果找不到对应的城市名称，抛出ValueError。
            raise ValueError(f'location {city_name} not found, availables are {self.city_df["中文名"].tolist()}')
        else:
            # 返回找到的第一个adcode。
            return filtered_df['adcode'].values[0]

    # call 方法：这是工具的实际执行逻辑。当AI模型决定调用此工具时，会执行此方法。
    # params: 包含工具调用所需的参数，通常是一个字典，键为参数名（如'location'）。
    def call(self, params):
        # 确保 params 是字典类型。如果DashScope返回的是字符串，则尝试解析为JSON。
        if isinstance(params, str):
            params = json.loads(params)
        
        # 获取位置参数。
        location = params.get('location')
        if not location:
            # 如果缺少必需的location参数，抛出ValueError。
            raise ValueError("Location parameter is missing for AmapWeather tool.")
        
        try:
            # 根据提供的地理位置名称获取其adcode。
            city_adcode = self.get_city_adcode(location)
            # 调试信息：打印即将发起的高德API请求URL。
            request_url = self.url.format(city=city_adcode, key=self.token)
            print(f"DEBUG: AmapWeather Request URL: {request_url}")
            
            # 发送GET请求到高德天气API。
            response = requests.get(request_url)
            # 检查HTTP响应状态码，如果不是2xx，则抛出HTTPError。
            response.raise_for_status()
            # 解析API返回的JSON数据。
            data = response.json()
            # 调试信息：打印高德API返回的原始响应数据。
            print(f"DEBUG: AmapWeather Raw Response Data: {data}")
            # 检查高德API的业务状态码（'status'字段）。'0'通常表示请求失败。
            if data['status'] == '0':
                # 如果API返回失败，统一处理错误信息。
                return json.dumps({"error": f"Amap API Error: {data.get('info', 'Unknown error')}"})
            else:
                # 成功时，从响应中提取天气和温度信息。
                weather = data['lives'][0]['weather']
                temperature = data['lives'][0]['temperature']
                # 返回JSON格式的天气信息，包括天气、温度和查询的地点。
                return json.dumps({"weather": weather, "temperature": temperature, "location": location})
        except Exception as e:
            # 捕获并处理调用高德API过程中可能发生的任何异常。
            return json.dumps({"error": f"Error calling AmapWeather tool: {str(e)}"})

# 实例化 AmapWeather 工具。
# 在这里传入 WEATHER_API 环境变量作为token，确保API Key被正确配置。
amap_weather_tool = AmapWeather(cfg={'token': os.environ.get('WEATHER_API', '')})

# --- 为通义千问模型定义工具列表 ---
# 这个列表以 DashScope 模型所需的格式定义了所有可用的工具。
# 模型会根据其内部逻辑和用户输入，选择并调用这些工具。
TOOLS = [{
    "type": "function", # 工具类型，这里是函数工具
    "function": {
        "name": amap_weather_tool.name,         # 工具的名称
        "description": amap_weather_tool.description, # 工具的描述
        "parameters": { # 工具的参数定义，遵循JSON Schema规范
            "type": "object",
            "properties": {
                # 动态生成参数属性，根据 AmapWeather 类的 parameters 列表
                param['name']: {"type": param['type'], "description": param['description']}
                for param in amap_weather_tool.parameters
            },
            # 动态生成必需参数列表
            "required": [param['name'] for param in amap_weather_tool.parameters if param.get('required')]
        }
    }
}]

# --- call_qwen_for_diagnosis 函数：调用大模型进行病情诊断 ---
def call_qwen_for_diagnosis(symptoms, severity, duration, additional_info):
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        return {"error": "DASHSCOPE_API_KEY is not set in environment variables."}

    # 构建系统消息，指导大模型扮演专业医生并输出特定JSON格式的诊断结果。
    system_prompt = f"""
你是一位专业的医疗诊断助手。根据用户提供的症状、严重程度、持续时间和任何附加信息，请你进行详细的病情分析，并以严格的JSON格式输出结果。请确保JSON结构和内容严格符合以下定义，不要有任何额外文本、解释或格式错误。所有建议应专业、具体且实用。

JSON输出格式（所有字段必须包含）：
{{
  "urgency_level": "string", // 紧急程度："高"（立即就医）、"中"（尽快就医）、"低"（可观察，必要时就医）
  "possible_diseases": [
    {{"name": "string", "confidence": "float"}}, // 可能的疾病名称及其置信度（0.0-1.0）
    // ... 更多可能的疾病
  ],
  "recommended_departments": ["string"], // 推荐就诊科室列表
  "analysis": "string", // 对症状的详细医学分析
  "recommendations": {{
    "immediate_actions": ["string"], // 立即采取的措施
    "lifestyle_advice": ["string"],  // 生活方式建议
    "when_to_see_doctor": ["string"], // 何时需要就医的指征
    "prevention_tips": ["string"]    // 预防建议
  }}
}}

请严格遵守JSON格式，不要输出任何Markdown格式，不要有任何前言或后语。
"""

    user_message = f"""
我的症状是：{', '.join(symptoms) if isinstance(symptoms, list) else symptoms}
严重程度：{severity}
持续时间：{duration}
附加信息：{additional_info}

请根据以上信息，输出详细的病情诊断，严格按照您被指示的JSON格式。
"""

    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_message}
    ]

    try:
        response = Generation.call(
            model='qwen-max', # 或 qwen-plus，根据需要选择
            api_key=api_key,
            messages=messages,
            result_format='message',
        )
        print(f"DEBUG: Type of response object from Generation.call: {type(response)}") # NEW: Check type immediately
        print(f"DEBUG: Raw DashScope Diagnosis Response (non-stream): {response}") # 打印原始响应

        # Safely get status_code, output, and choices
        status_code = getattr(response, 'status_code', None)
        output = getattr(response, 'output', None)
        choices = getattr(output, 'choices', None) if output else None

        full_content = "" # 显式初始化
        
        # 严格检查响应结构
        if status_code == 200 and isinstance(output, object) and isinstance(choices, list) and len(choices) > 0:
            print(f"DEBUG: Diagnosis Response Output: {output}") # 打印 output
            print(f"DEBUG: Diagnosis Response Choices: {choices}") # 打印 choices
            
            first_choice = choices[0]
            message = getattr(first_choice, 'message', None)
            content = getattr(message, 'content', None) if message else None

            if content is not None and isinstance(content, str):
                print(f"DEBUG: Type of content before assignment: {type(content)}")
                print(f"DEBUG: Content before assignment: '''{content}'''")
                full_content = content # 直接赋值，因为它已经是字符串
            else:
                print("DEBUG: No valid content found in diagnosis response choice.")
                return {"error": "大模型诊断返回内容为空或格式不正确"}
        else:
            # 更具体的错误消息
            error_message = f"DashScope Resp for diagnosis not OK. Status: {status_code}, Output valid: {output is not None}, Choices valid: {choices is not None and len(choices) > 0}"
            print(f"DEBUG: {error_message}")
            return {"error": f"大模型诊断失败: {error_message}"}

        # 尝试解析大模型返回的JSON字符串
        try:
            # 显式去除潜在的BOM和所有空白字符
            cleaned_full_content = full_content.strip()
            if cleaned_full_content.startswith(codecs.BOM_UTF8.decode('utf-8')):
                cleaned_full_content = cleaned_full_content[len(codecs.BOM_UTF8.decode('utf-8')):]
            cleaned_full_content = cleaned_full_content.strip() # 移除BOM后再次strip，以防有新的空白
            
            # NEW: Precisely extract JSON content by finding first '{' and last '}'
            start_index = cleaned_full_content.find('{')
            end_index = cleaned_full_content.rfind('}')

            if start_index == -1 or end_index == -1 or end_index < start_index:
                raise ValueError("无法在内容中找到有效的JSON对象边界")

            final_json_string = cleaned_full_content[start_index : end_index + 1]

            print(f"DEBUG: Final JSON string for parsing (type: {type(final_json_string)}): '''{final_json_string}'''")
            diagnosis_data = json.loads(final_json_string)
            return {"success": True, "data": diagnosis_data}
        except json.JSONDecodeError as e:
            print(f"DEBUG: JSON decoding error from LLM: {e}")
            print(f"DEBUG: LLM raw response (during error): '''{full_content}'''") # Keep original full_content for debugging
            return {"error": f"大模型返回的诊断数据格式错误: {str(e)}. 原始回复: {full_content[:200]}..."}
        except ValueError as e:
            print(f"DEBUG: Value error during JSON extraction: {e}")
            print(f"DEBUG: LLM raw response (during error - extraction): '''{full_content}'''")
            return {"error": f"大模型返回内容无法提取JSON: {str(e)}. 原始回复: {full_content[:200]}..."}

    except Exception as e:
        print(f"DEBUG: Outer exception caught in call_qwen_for_diagnosis: {type(e).__name__}: {e}")
        return {"error": f"调用大模型进行诊断失败: {type(e).__name__}: {str(e)}"}

# --- call_qwen_api 函数（核心AI交互逻辑）---
# 该函数负责与通义千问大模型进行交互，处理用户消息、工具调用和模型响应。
def call_qwen_api(message, context=None):
    # 从环境变量中获取 DashScope API Key。这是访问大模型服务的凭证。
    api_key = os.getenv("DASHSCOPE_API_KEY")
    print(f"DEBUG: DASHSCOPE_API_KEY value: {api_key}") # 临时调试信息，检查API Key是否加载
    """调用通义千问大模型API"""
    if not api_key:
        # 如果API Key未设置，返回错误信息。
        return {"error": "DASHSCOPE_API_KEY is not set in environment variables."}

    # 构建发送给大模型的消息列表。
    # 初始包含一个系统消息，设定AI的身份、能力和行为指南，特别是如何使用工具。
    messages = [
        {'role': 'system', 'content': '你是一位专业的医疗医生，知道一切的医学知识，同时你也可以获取实时天气信息。请以专业、简洁的口吻回答用户的问题，提供医学建议和指导。请直接开始回答，避免任何形式的寒暄或重复的问候。切记要专业，不要出现任何重复语言，只输出最后的答案。当用户问到天气相关问题时，你应该调用 `amap_weather` 工具来获取天气数据。在调用 `amap_weather` 工具时，`location` 参数请务必提供详细的区或县名称，例如"海淀区"、"锦江区"，而不是笼统的城市名如"北京"或"成都"。'}
    ]
    # 如果有历史对话上下文，将其添加到消息列表中。
    if context and 'history' in context:
        for item in context['history']:
            if 'user' in item:
                messages.append({'role': 'user', 'content': item['user']})
            if 'ai' in item:
                messages.append({'role': 'assistant', 'content': item['ai']})
    
    # 将当前用户消息添加到消息列表的末尾。
    messages.append({'role': 'user', 'content': message})

    try:
        # --- 第一次调用大模型：让模型决定是否需要调用工具 ---
        # `Generation.call` 是 DashScope SDK 调用大模型的核心方法。
        # model: 使用的模型名称，例如 'qwen-max'。
        # api_key: 访问模型的API Key。
        # messages: 当前对话的消息历史。
        # seed: 随机种子，用于控制模型生成结果的确定性（方便调试和复现）。
        # stream: True 表示以流式方式获取模型响应。
        # result_format: 'message' 表示返回结构化的消息对象。
        # tools: 传入我们定义的工具列表，模型会根据此列表决定是否进行工具调用。
        response_generator = Generation.call(
            model='qwen-max',
            api_key=api_key,
            messages=messages,
            seed=1234,
            stream=True,
            result_format='message',
            tools=TOOLS # 传入工具列表，让模型知道有哪些工具可用
        )
        
        full_content = "" # 用于累积模型返回的文本内容
        last_complete_tool_calls = [] # 用于存储模型返回的完整工具调用列表

        # 遍历流式响应，处理模型的输出。
        for resp in response_generator:
            print(f"DEBUG: Raw DashScope Resp: {resp}") # 调试信息：打印原始响应
            if resp.status_code == 200: # 检查HTTP状态码是否成功
                if resp.output: # 检查响应输出是否存在
                    print(f"DEBUG: DashScope Resp Output: {resp.output}") # 调试信息
                    if hasattr(resp.output, 'choices') and resp.output.choices is not None:
                        print(f"DEBUG: DashScope Resp Choices: {resp.output.choices}") # 调试信息
                        for choice in resp.output.choices:
                            try:
                                if choice.message: # 检查消息体是否存在
                                    # 安全地获取文本内容，处理可能为None的情况。
                                    current_content = getattr(choice.message, 'content', None)
                                    if current_content is not None:
                                        full_content = current_content # 累积文本内容
                                    else:
                                        print("DEBUG: choice.message has no content or it's None.")

                                    # 安全地获取工具调用列表。
                                    current_tool_calls = getattr(choice.message, 'tool_calls', None)
                                    if current_tool_calls is not None:
                                        # 只有当 tool_calls 非空时才更新，确保我们拿到的是完整的工具调用指令。
                                        if current_tool_calls:
                                            last_complete_tool_calls = current_tool_calls
                                    else:
                                        print("DEBUG: choice.message has no tool_calls attribute or it's None.")
                                else:
                                    print("DEBUG: choice.message is None.")
                            except Exception as e: # 捕获处理 choice.message 时的异常
                                print(f"DEBUG: Exception caught during choice.message processing: {e}, type: {type(e)}")
                                continue # 继续处理下一个 choice
                    else:
                        print("DEBUG: resp.output.choices is None or missing.")
                else:
                    print("DEBUG: resp.output is None.")
            else:
                print(f"DEBUG: DashScope Resp not OK or missing output/choices: {resp}")

        # --- 处理工具调用：在模型第一次生成响应后执行 ---
        valid_tool_calls_to_execute = [] # 存储有效的、可执行的工具调用
        if last_complete_tool_calls: # 如果模型返回了工具调用
            for tool_call in last_complete_tool_calls:
                # 验证工具调用结构是否正确。
                if isinstance(tool_call, dict) and 'function' in tool_call and isinstance(tool_call['function'], dict) and 'name' in tool_call['function']:
                    function_name = tool_call['function']['name'] # 获取函数名称
                    # 获取参数字符串，如果不存在则默认为空JSON对象。
                    function_args_str = tool_call['function'].get('arguments', '{}')
                    
                    try:
                        # 尝试解析工具参数为JSON对象。
                        function_args = json.loads(function_args_str)
                        # 如果解析成功，将工具调用信息添加到待执行列表。
                        valid_tool_calls_to_execute.append({
                            "name": function_name,
                            "args": function_args,
                            "id": tool_call.get('id', 'unknown_id') # 确保工具调用ID被传递
                        })
                    except json.JSONDecodeError:
                        print(f"DEBUG: Skipping malformed tool_call arguments: {function_args_str}")
                        # 如果参数解析失败，跳过此工具调用。
                else:
                    print(f"DEBUG: Skipping malformed tool_call format: {tool_call}")

        print(f"DEBUG: Processed Tool Calls for execution: {valid_tool_calls_to_execute}") # 打印最终处理的工具调用列表

        # --- 如果模型决定调用工具，则执行工具并进行第二次模型调用 ---
        if valid_tool_calls_to_execute:
            # Step 1: 将AI助手的响应（包含工具调用）添加到消息历史。
            # 这是为了让模型知道它之前发出了哪些工具调用指令。
            assistant_tool_call_message = {
                "role": "assistant",
                "content": full_content, # 第一次调用中模型可能生成的文本内容
                "tool_calls": last_complete_tool_calls # 第一次调用中模型生成的工具调用列表
            }
            messages.append(assistant_tool_call_message)

            # Step 2: 遍历所有有效的工具调用，执行它们并将结果添加到消息历史。
            for tool_call_info in valid_tool_calls_to_execute:
                function_name = tool_call_info['name']
                function_args = tool_call_info['args']
                tool_call_id = tool_call_info['id']

                if function_name == "amap_weather":
                    # 如果是天气工具，则调用 AmapWeather 实例的 call 方法。
                    tool_response_data = amap_weather_tool.call(function_args)
                    print(f"DEBUG: AmapWeather Tool Response: {tool_response_data}") # 调试信息
                    # 将工具执行结果以 'tool' 角色添加到消息历史。
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id, # 对应模型的工具调用ID
                        "content": tool_response_data
                    })
                else:
                    # 如果是未知工具，返回错误信息。
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": json.dumps({"error": f"Unknown tool: {function_name}"})
                    })
            
            # --- 第二次调用大模型：将工具执行结果传回模型，获取最终回复 ---
            # 模型在接收到工具结果后，可以基于这些信息生成更准确的回复。
            print(f"DEBUG: Messages before second pass: {messages}") # 调试信息
            second_response_generator = Generation.call(
                model='qwen-max',
                api_key=api_key,
                messages=messages, # 包含工具调用和工具结果的完整消息历史
                seed=1234,
                stream=True,
                result_format='message'
                # 在第二轮中通常不再需要传入 tools=TOOLS，因为模型已经知道如何根据结果回复。
            )
            
            full_content = "" # 重置 full_content 以捕获第二次调用的回复

            # 遍历第二次流式响应，获取最终的文本回复。
            for resp in second_response_generator:
                print(f"DEBUG: Raw DashScope Resp (second pass): {resp}") # 调试信息
                if resp.status_code == 200:
                    if resp.output:
                        print(f"DEBUG: DashScope Resp Output (second pass): {resp.output}") # 调试信息
                        if hasattr(resp.output, 'choices') and resp.output.choices is not None:
                            print(f"DEBUG: DashScope Resp Choices (second pass): {resp.output.choices}") # 调试信息
                            for choice in resp.output.choices:
                                try:
                                    if choice.message:
                                        current_content = getattr(choice.message, 'content', None)
                                        if current_content is not None:
                                            full_content = current_content
                                        else:
                                            print("DEBUG: choice.message (second pass) has no content or it's None.")
                                    else:
                                        print("DEBUG: choice.message (second pass) is None.")
                                except Exception as e:
                                    print(f"DEBUG: Unexpected error during choice.message (second pass) processing: {e}, type: {type(e)}")
                                    continue
                        else:
                            print("DEBUG: resp.output.choices is None or missing.")
                    else:
                        print("DEBUG: resp.output is None.")
                else:
                    print(f"DEBUG: DashScope Resp (second pass) not OK or missing output/choices: {resp}")
        
        # 返回最终的AI回复。如果第二次调用没有生成内容（例如模型只返回工具调用），则返回空字符串。
        return {"success": True, "response": full_content if full_content else ""}
    except Exception as e:
        # 捕获并处理调用大模型API过程中可能发生的任何错误。
        print(f"DEBUG: Exception caught in call_qwen_api: {e}, type: {type(e)}") # 调试信息
        return {"error": f"调用通义千问API失败: {str(e)}"}

# --- 辅助函数：格式化AI回复 ---
# 用于将 call_qwen_api 的原始响应格式化为用户友好的字符串。
def format_ai_response(response_data):
    """格式化AI回复"""
    if response_data.get("success"):
        return response_data["response"]
    else:
        return f"AI助手服务异常：{response_data.get('error', '未知错误')}"

# --- Flask 路由：/ai/chat （AI助手对话API）---
# 处理来自前端的AI聊天请求。
@ai_bp.route('/ai/chat', methods=['POST'])
def chat_with_ai():
    print("DEBUG: chat_with_ai route accessed.") # 临时调试信息
    """AI助手对话API"""
    try:
        data = request.get_json() # 获取JSON格式的请求体
        
        if not data:
            return jsonify({"error": "请提供对话内容"}), 400
        
        message = data.get('message', '') # 获取用户消息内容
        context = data.get('context', {}) # 获取历史对话上下文（可选）
        
        if not message:
            return jsonify({"error": "请提供有效的消息内容"}), 400
        
        # 调用核心函数与通义千问API交互。
        qwen_response = call_qwen_api(message, context)
        # 格式化模型返回的响应。
        formatted_response = format_ai_response(qwen_response)
        
        if qwen_response.get("success"):
            # 如果成功，返回成功状态和格式化后的数据。
            return jsonify({
                "success": True,
                "data": {
                    "response": formatted_response,
                    "raw_data": qwen_response.get("response"), # 存储原始模型回复以供调试/分析
                    "timestamp": "2024-01-01T00:00:00Z"  # 实际应用中应使用真实时间戳
                }
            })
        else:
            # 如果失败，返回失败状态和错误信息。
            return jsonify({
                "success": False,
                "error": formatted_response # 错误信息
            }), 500
        
    except Exception as e:
        # 捕获并处理整个API请求处理过程中的异常。
        return jsonify({"error": f"AI对话过程中出现错误: {str(e)}"}), 500

# --- Flask 路由：/ai/health-advice （获取健康建议API）---
# 这是一个独立的API，用于基于症状获取健康建议。
@ai_bp.route('/ai/health-advice', methods=['POST'])
def get_health_advice():
    print("DEBUG: /ai/health-advice route accessed.") # 临时调试信息
    """获取健康建议API"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "请提供症状信息"}), 400
        
        symptoms = data.get('symptoms', []) # 获取症状列表
        # analysis_result = data.get('analysis_result', {}) # 这个字段现在将由大模型直接生成
        severity = data.get('severity', '中等')
        duration = data.get('duration', '1-2天')
        additional_info = data.get('additional_info', '')
        
        if not symptoms:
            return jsonify({"error": "请提供症状信息"}), 400
        
        # 调用大模型进行诊断
        diagnosis_response = call_qwen_for_diagnosis(symptoms, severity, duration, additional_info)
        print(f"DEBUG: Diagnosis Response from call_qwen_for_diagnosis: {diagnosis_response}")

        if diagnosis_response.get("success"):
            llm_analysis_data = diagnosis_response.get("data")
            
            # 映射大模型的输出到现有前端所需的格式
            # 这里假设大模型的输出与前端期望的analysisResult结构非常接近
            # 否则需要进行更复杂的映射或调整前端期望的结构
            
            # 提取大模型提供的紧急程度
            urgency_level = llm_analysis_data.get('urgency_level', '低')
            
            # 直接使用大模型提供的推荐建议
            recommendations_from_llm = llm_analysis_data.get('recommendations', {})
            
            return jsonify({
                "success": True,
                "data": {
                    "analysis": { # 这里的analysis是旧的generate_ai_response的analysis_result结构
                        "urgency_level": urgency_level,
                        "possible_diseases": llm_analysis_data.get('possible_diseases', []),
                        "recommended_departments": llm_analysis_data.get('recommended_departments', []),
                        "advice": [llm_analysis_data.get('analysis', '')], # 大模型的详细分析作为advice，封装为数组以匹配前端期望
                    },
                    "recommendations": { # 直接使用大模型提供的分类建议
                        "immediate_actions": recommendations_from_llm.get('immediate_actions', []),
                        "lifestyle_advice": recommendations_from_llm.get('lifestyle_advice', []),
                        "when_to_see_doctor": recommendations_from_llm.get('when_to_see_doctor', []),
                        "prevention_tips": recommendations_from_llm.get('prevention_tips', []),
                    },
                    "urgency_level": urgency_level, # 保持与旧接口兼容
                    "disclaimer": "以上建议由AI大模型生成，仅供参考，不能替代专业医疗诊断。请根据实际情况咨询医生。"
                }
            })
        else:
            # 如果大模型调用失败，返回错误信息
            return jsonify({"error": diagnosis_response.get("error", "大模型诊断服务异常")}), 500
        
    except Exception as e:
        return jsonify({"error": f"获取健康建议时出现错误: {str(e)}"}), 500

# --- Flask 路由：/ai/emergency-check （紧急情况检查API）---
# 用于根据用户提供的症状判断是否存在紧急情况。
@ai_bp.route('/ai/emergency-check', methods=['POST'])
def emergency_check():
    """紧急情况检查API"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "请提供症状信息"}), 400
        
        symptoms = data.get('symptoms', []) # 获取症状列表
        severity = data.get('severity', '中等') # 获取症状严重程度
        
        # 预定义的紧急症状关键词列表。
        emergency_keywords = [
            "胸痛", "呼吸困难", "意识模糊", "剧烈头痛", "大量出血",
            "严重腹痛", "高热不退", "抽搐", "昏迷", "心悸"
        ]
        
        # 检查用户提供的症状中是否包含紧急关键词。
        emergency_detected = False
        detected_emergency_symptoms = []
        
        for symptom in symptoms:
            for emergency_keyword in emergency_keywords:
                if emergency_keyword in symptom:
                    emergency_detected = True
                    detected_emergency_symptoms.append(emergency_keyword)
        
        # 如果严重程度被标记为"严重"，也视为紧急情况。
        if severity == "严重":
            emergency_detected = True
        
        # 构建响应体。
        response = {
            "is_emergency": emergency_detected,         # 是否检测到紧急情况
            "detected_symptoms": detected_emergency_symptoms, # 检测到的紧急症状
            "recommendation": "",                       # 推荐建议
            "emergency_contacts": {                     # 紧急联系电话
                "emergency_number": "120",
                "poison_control": "400-161-9595",
                "mental_health_hotline": "400-161-9995",
            }
        }
        
        # 根据是否检测到紧急情况，提供不同的推荐建议。
        if emergency_detected:
            response["recommendation"] = "检测到可能的紧急情况，建议立即拨打120急救电话或前往最近的急诊科！"
        else:
            response["recommendation"] = "暂未检测到紧急情况，但请继续关注症状变化。如有担心，建议咨询医生。"
        
        return jsonify({
            "success": True,
            "data": response
        })
        
    except Exception as e:
        return jsonify({"error": f"紧急情况检查时出现错误: {str(e)}"}), 500

