# =============================================================================
# AI 问答服务模块
# =============================================================================
# 功能说明：
#   - 封装 DeepSeek API 调用
#   - 提供问答功能
#   - 支持多轮对话
#
# 使用示例：
#   from app.services.qa_service import qa_service
#   response = qa_service.ask("什么是水果成熟度检测？")
#
# DeepSeek API 文档：https://platform.deepseek.com/api-docs/zh
# =============================================================================

import json
import time
from typing import List, Dict, Any, Optional

import requests

from app.config import settings


class QAService:
    """
    AI 问答服务类
    
    封装 DeepSeek API，提供问答功能
    """
    
    def __init__(self):
        """
        初始化问答服务
        """
        self.api_key = settings.deepseek.api_key
        self.api_url = settings.deepseek.api_url
        self.model = settings.deepseek.model
        self.timeout = settings.deepseek.timeout
        self.max_tokens = settings.deepseek.max_tokens
        self.temperature = settings.deepseek.temperature
        
        # 系统提示词，定义 AI 助手的角色和行为
        self.system_prompt = """
你是一个专业的果园水果检测AI助手，擅长解答关于水果识别、成熟度判断、病虫害检测等问题。

你的知识库包括：
1. **水果种类识别**：香蕉、芒果、荔枝等常见水果的特征识别
   - 香蕉：未成熟时呈绿色，成熟时呈黄色
   - 芒果：未成熟时呈绿色，成熟时呈黄色或橙色
   - 荔枝：未成熟时呈绿色或黄绿色，成熟时呈红色或紫红色
2. **成熟度判断**：基于颜色、形状、大小等特征判断水果成熟度
3. **病虫害检测**：识别常见的水果病虫害症状
4. **检测技术**：介绍YOLO等目标检测技术在水果检测中的应用

请用友好、专业的语言回答用户问题，确保信息准确易懂。
        """.strip()
    
    def _build_request(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        构建 API 请求体
        
        参数：
            messages: 对话消息列表，格式为 [{"role": "user|assistant|system", "content": "..."}]
        
        返回：
            请求体字典
        """
        return {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": False
        }
    
    def _build_headers(self) -> Dict[str, str]:
        """
        构建请求头
        
        返回：
            请求头字典
        """
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def ask(self, question: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        发送问答请求
        
        参数：
            question: 用户问题
            history: 历史对话记录（可选），格式为 [{"role": "user|assistant", "content": "..."}]
        
        返回：
            AI 回答内容
        
        抛出：
            Exception: API 调用失败时抛出异常
        """
        if not self.api_key or self.api_key == "your_deepseek_api_key_here":
            return "请先配置 DeepSeek API 密钥（在 .env 文件中设置 DEEPSEEK_API_KEY）"
        
        # 构建消息列表
        messages = []
        
        # 添加系统提示词
        messages.append({"role": "system", "content": self.system_prompt})
        
        # 添加历史对话
        if history:
            messages.extend(history)
        
        # 添加当前问题
        messages.append({"role": "user", "content": question})
        
        # 构建请求
        request_body = self._build_request(messages)
        headers = self._build_headers()
        
        try:
            # 发送请求
            response = requests.post(
                self.api_url,
                headers=headers,
                data=json.dumps(request_body, ensure_ascii=False),
                timeout=self.timeout
            )
            
            # 检查响应状态
            if response.status_code != 200:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json.get("error", {}).get("message", error_detail)
                except:
                    pass
                raise Exception(f"API 请求失败 (HTTP {response.status_code}): {error_detail}")
            
            # 解析响应
            result = response.json()
            
            # 提取回答内容
            if result.get("choices") and len(result["choices"]) > 0:
                answer = result["choices"][0]["message"]["content"]
                return answer.strip()
            
            raise Exception("API 响应格式错误")
        
        except requests.exceptions.Timeout:
            raise Exception("请求超时，请稍后重试")
        except requests.exceptions.ConnectionError:
            raise Exception("网络连接失败，请检查网络连接")
        except Exception as e:
            raise Exception(f"问答服务异常: {str(e)}")
    
    def ask_stream(self, question: str, history: Optional[List[Dict[str, str]]] = None):
        """
        流式问答请求（生成器）
        
        参数：
            question: 用户问题
            history: 历史对话记录（可选）
        
        返回：
            生成器，逐块返回 AI 回答内容
        """
        if not self.api_key or self.api_key == "your_deepseek_api_key_here":
            yield "请先配置 DeepSeek API 密钥（在 .env 文件中设置 DEEPSEEK_API_KEY）"
            return
        
        # 构建消息列表
        messages = []
        messages.append({"role": "system", "content": self.system_prompt})
        
        if history:
            messages.extend(history)
        
        messages.append({"role": "user", "content": question})
        
        # 构建请求（流式模式）
        request_body = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": True
        }
        headers = self._build_headers()
        
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                data=json.dumps(request_body, ensure_ascii=False),
                timeout=self.timeout,
                stream=True
            )
            
            if response.status_code != 200:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json.get("error", {}).get("message", error_detail)
                except:
                    pass
                raise Exception(f"API 请求失败 (HTTP {response.status_code}): {error_detail}")
            
            # 流式解析响应
            for line in response.iter_lines():
                if line:
                    line = line.decode("utf-8").strip()
                    if line.startswith("data: "):
                        line = line[6:]  # 移除 "data: " 前缀
                        if line == "[DONE]":
                            break
                        try:
                            chunk = json.loads(line)
                            if chunk.get("choices") and len(chunk["choices"]) > 0:
                                delta = chunk["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
        
        except requests.exceptions.Timeout:
            yield "请求超时，请稍后重试"
        except requests.exceptions.ConnectionError:
            yield "网络连接失败，请检查网络连接"
        except Exception as e:
            yield f"问答服务异常: {str(e)}"


# =============================================================================
# 创建全局问答服务实例
# =============================================================================
qa_service = QAService()
