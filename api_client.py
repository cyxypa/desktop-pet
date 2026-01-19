import os
import json
from datetime import datetime
from PyQt5.QtCore import QThread, pyqtSignal
from openai import OpenAI

class ApiWorker(QThread):
    """后台处理API请求的线程类"""
    result_ready = pyqtSignal(str)
    
    def __init__(self, client, text, history_file):
        super().__init__()
        self.client = client
        self.text = text
        self.history_file = history_file


    def run(self):
        prompt="""请你扮演一位拥有 10 年以上开发经验的资深程序员，具备多领域技术栈积累和丰富的实战经验。在与我交流时，需遵循以下原则：
角色定位
精通 Python、Java、JavaScript、C++ 等主流编程语言，熟悉前端（Vue/React）、后端（SpringBoot/Django）、数据库（MySQL/Redis）、算法与数据结构等技术领域。
具备系统设计、性能优化、bug 排查、代码重构等实战能力，能从工程化角度给出专业解决方案。
回应要求
精准解答：针对编程问题（语法错误、逻辑漏洞、功能实现等），先定位核心问题，再提供具体解决方案，避免模糊表述。
代码规范：给出的代码示例需符合行业规范（如命名规则、注释清晰），可直接运行或稍作调整即可使用。
逻辑清晰：复杂问题需分步骤拆解，用 “问题分析→解决方案→优化建议” 的结构呈现，必要时结合流程图或伪代码说明。
延伸指导：除解决当前问题外，补充相关技术原理、避坑指南或最佳实践（如 “这段代码在高并发场景下可能存在线程安全问题，建议使用 XX 锁机制”）。
适配场景：根据问题背景（如开发环境、业务需求）调整方案，例如区分 “快速原型开发” 和 “生产环境部署” 的不同实现思路。
当我提出编程相关问题时，请以专业、务实的风格回应，优先解决实际问题，再进行技术拓展。若涉及未明确的信息（如编程语言版本、框架类型），请先询问确认，再给出针对性解答。
"""
        try:
            # 加载历史记录作为上下文
            messages = [{"role": "system", "content":prompt}]
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                    # 只取最近5条对话作为上下文
                    for item in history[-5:]:
                        messages.append({"role": "user", "content": item["user"]})
                        messages.append({"role": "assistant", "content": item["assistant"]})
            
            # 添加当前查询
            messages.append({"role": "user", "content": self.text})
            
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                stream=False
            )
            api_response = response.choices[0].message.content
            self.result_ready.emit(api_response)
        except Exception as e:
            self.result_ready.emit(f"API请求失败: {str(e)}")

class ApiClient:
    """API客户端类，处理API初始化和历史记录"""
    def __init__(self, api_key, base_url, history_file="chat_history.json"):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.history_file = history_file
        self.init_history_file()
        
    def init_history_file(self):
        """初始化对话历史文件"""
        if not os.path.exists(self.history_file):
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
    
    def save_to_history(self, user_input, assistant_response):
        """保存对话到历史记录"""
        try:
            history = []
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            
            history.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "user": user_input,
                "assistant": assistant_response
            })
            
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存历史记录失败: {str(e)}")
    
    def get_history_text(self):
        """获取格式化的历史记录（日期显示为蓝色，设置合适字体大小）"""
        try:
            if not os.path.exists(self.history_file):
                return "暂无对话历史"
            
            with open(self.history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            if not history:
                return "暂无对话历史"
            
            # 使用HTML格式，并设置字体大小、行高和颜色
            history_text = """
            <html>
                <body style="
                    font-family: Microsoft YaHei; 
                    font-size: 14px;  /* 核心：设置字体大小 */
                    line-height: 1.6;  /* 行高，提升可读性 */
                    color: #333;       /* 文字颜色 */
                ">
            """
            history_text += "<h3 style='margin: 0 0 10px 0;'>对话历史:</h3>"
            for item in history:
                # 日期设为蓝色，加粗
                history_text += f"<p style='color: #0066CC; margin: 8px 0 4px 0; font_size: 20px; font-weight: bold;'>[{item['timestamp']}]</p>"
                # 用户输入
                history_text += f"<p style='margin: 4px 0;font-size: 24px;'><strong>user:</strong> {item['user'].replace('\n', '<br>')}</p>"
                # 助手回复
                history_text += f"<p style='margin: 4px 0 15px 0;font-size: 24px;'><strong>assistant:</strong> {item['assistant'].replace('\n', '<br>')}</p>"
            history_text += "</body></html>"
            return history_text
        except Exception as e:
            return f"读取历史记录失败: {str(e)}"
