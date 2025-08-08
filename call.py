import requests
from openai import OpenAI
import openai
import time
import json


class ChatClient:
    def __init__(self, model, url, temperature=0.7, top_p=1, max_tokens=8192, api_key=None):
        self.model = model
        self.url = url
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.api_key = api_key
        self.conversation_history = []
        
        # 初始化OpenAI客户端
        self.client = OpenAI(
            api_key=api_key,
            base_url=url
        )
    
    def add_message(self, role, content):
        """添加消息到对话历史"""
        self.conversation_history.append({"role": role, "content": content})
    
    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []
    
    def get_history(self):
        """获取对话历史"""
        return self.conversation_history
    
    def chat_with_openai(self, user_input, use_history=True):
        """使用OpenAI客户端进行对话"""
        if use_history:
            # 添加用户输入到历史
            self.add_message("user", user_input)
            messages = self.conversation_history
        else:
            # 不使用历史，只发送当前消息
            messages = [{"role": "user", "content": user_input}]
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                top_p=self.top_p,
                max_tokens=self.max_tokens
            )
            
            print(response)
            assistant_response = response.choices[0].message.content
            
            if use_history:
                # 添加助手回复到历史
                self.add_message("assistant", assistant_response)
            
            return assistant_response
            
        except openai.RateLimitError:
            print("Rate limit exceeded. Waiting...")
            time.sleep(20)
            return self.chat_with_openai(user_input, use_history)  # 重试
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    def chat_with_requests(self, user_input, use_history=True):
        """使用requests进行对话"""
        if use_history:
            # 添加用户输入到历史
            self.add_message("user", user_input)
            messages = self.conversation_history
        else:
            # 不使用历史，只发送当前消息
            messages = [{"role": "user", "content": user_input}]
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": self.api_key
        }
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p
        }
        
        url = self.url.rstrip('/')
        if "chat/completions" not in url:
            url = url + "/chat/completions"
        
        try:
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                response_data = response.json()
                assistant_response = response_data['choices'][0]['message']['content']
                
                if use_history:
                    # 添加助手回复到历史
                    self.add_message("assistant", assistant_response)
                
                return assistant_response
            else:
                print(f"Error: {response.status_code}")
                print(response.text)
                return None
                
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    def interactive_chat(self, use_openai_client=True):
        """交互式多轮对话"""
        print("=== 多轮对话开始 ===")
        print("输入 'quit' 或 'exit' 退出")
        print("输入 'clear' 清空对话历史")
        print("输入 'history' 查看对话历史")
        print("-" * 50)
        
        while True:
            user_input = input("\n您: ").strip()
            
            if user_input.lower() in ['quit', 'exit']:
                print("再见！")
                break
            
            if user_input.lower() == 'clear':
                self.clear_history()
                print("对话历史已清空")
                continue
            
            if user_input.lower() == 'history':
                print("\n=== 对话历史 ===")
                for i, msg in enumerate(self.conversation_history, 1):
                    role = "您" if msg["role"] == "user" else "助手"
                    print(f"{i}. {role}: {msg['content']}")
                print("=" * 20)
                continue
            
            if not user_input:
                continue
            
            print("\n助手: ", end="", flush=True)
            
            # 选择使用哪种方式进行对话
            if use_openai_client:
                response = self.chat_with_openai(user_input)
            else:
                response = self.chat_with_requests(user_input)
            
            if response:
                print(response)
            else:
                print("抱歉，出现了错误，请重试。")
    
    def single_turn_chat(self, prompt, use_openai_client=True):
        """单轮对话（不保存历史）"""
        if use_openai_client:
            return self.chat_with_openai(prompt, use_history=False)
        else:
            return self.chat_with_requests(prompt, use_history=False)


def main():
    # 配置参数
    url = "http://yy.dbh.baidu-int.com/v1"
    api_key = "sk-va1zl4RPpU2XC43VnVfSB3marxgoTtyrUzcN5q7Pdtb9zAa5"
    model = "deepseek-r1-0528"
    temperature = 0.7
    max_tokens = 8192
    top_p = 1
    
    # 创建聊天客户端
    chat_client = ChatClient(
        model=model,
        url=url,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        api_key=api_key
    )
    
    # 选择使用方式
    print("选择使用方式:")
    print("1. 交互式多轮对话")
    print("2. 单轮对话测试")
    
    choice = input("请选择 (1 或 2): ").strip()
    
    if choice == "1":
        # 交互式多轮对话
        use_openai = input("使用OpenAI客户端? (y/n): ").strip().lower() == 'y'
        chat_client.interactive_chat(use_openai_client=use_openai)
    
    elif choice == "2":
        # 单轮对话测试
        prompt = input("请输入您的问题: ").strip()
        use_openai = input("使用OpenAI客户端? (y/n): ").strip().lower() == 'y'
        
        response = chat_client.single_turn_chat(prompt, use_openai_client=use_openai)
        if response:
            print(f"\n助手回复: {response}")
        else:
            print("请求失败")
    
    else:
        print("无效选择")


if __name__ == '__main__':
    main()