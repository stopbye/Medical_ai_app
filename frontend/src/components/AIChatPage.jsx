import { useState, useEffect, useRef } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card.jsx';
import { Input } from '@/components/ui/input.jsx';
import { Button } from '@/components/ui/button.jsx';
import { Send, MessageCircle, ArrowLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

// AIChatPage 函数组件：负责渲染AI医生聊天界面。
function AIChatPage() {
  const navigate = useNavigate();
  // messages 状态：存储聊天历史记录。
  // 初始值设置为一条AI发出的欢迎消息，其中包含主要功能和天气查询的示例。
  // 使用模板字符串（反引号`）可以方便地编写多行文本，保持格式。
  const [messages, setMessages] = useState([
    { sender: 'ai', text: `您好！我是您的智能医生助手。您可以向我咨询医疗问题，例如"感冒症状"或"附近医院"。

您也可以查询天气信息，例如"查询北京天气"或"上海今天天气怎么样"。` }
  ]);
  // inputMessage 状态：存储用户在输入框中键入的当前消息。
  const [inputMessage, setInputMessage] = useState('');
  // isLoading 状态：控制发送消息按钮和输入框的禁用状态，以及显示"AI正在思考..."的提示。
  const [isLoading, setIsLoading] = useState(false);
  // chatEndRef：用于引用聊天内容的底部，以便新消息到来时可以自动滚动。
  const chatEndRef = useRef(null);

  // scrollToBottom 函数：将聊天区域滚动到最底部，显示最新消息。
  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // useEffect 钩子：在 messages 状态更新时调用 scrollToBottom，确保新消息可见。
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // handleSendMessage 函数：处理用户发送消息的逻辑。
  const handleSendMessage = async () => {
    // 如果输入消息为空或只包含空格，则不发送。
    if (inputMessage.trim() === '') return;

    // 创建新的用户消息对象。
    const newUserMessage = { sender: 'user', text: inputMessage };
    // 更新消息列表，将新用户消息添加到末尾。
    setMessages((prevMessages) => [...prevMessages, newUserMessage]);
    // 清空输入框。
    setInputMessage('');
    // 设置加载状态为true，显示加载指示器。
    setIsLoading(true);

    try {
      // 构建历史消息，以便发送给AI模型作为上下文。
      // 格式转换为 { user: "...", ai: "..." } 形式。
      const history = messages.map(msg => ({ [msg.sender]: msg.text }));
      // 发送POST请求到后端AI聊天API。
      const response = await fetch('/api/ai/chat', { // 假设API端点是 /api/ai/chat
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        // 请求体包含当前用户消息和历史上下文。
        body: JSON.stringify({ message: inputMessage, context: { history } }),
      });

      // 解析后端返回的JSON数据。
      const data = await response.json();
      if (data.success) {
        // 如果后端成功返回AI回复，则添加到消息列表中。
        const aiResponse = { sender: 'ai', text: data.data.response };
        setMessages((prevMessages) => [...prevMessages, aiResponse]);
      } else {
        // 如果后端返回错误，则显示错误消息。
        const errorMessage = { sender: 'ai', text: `AI助手服务异常: ${data.error || '未知错误'}` };
        setMessages((prevMessages) => [...prevMessages, errorMessage]);
      }
    } catch (error) {
      // 捕获并处理网络请求或JSON解析错误。
      console.error('Error sending message:', error);
      const errorMessage = { sender: 'ai', text: '与AI助手通信失败，请稍后再试。' };
      setMessages((prevMessages) => [...prevMessages, errorMessage]);
    } finally {
      // 无论请求成功或失败，最后都将加载状态设置为false。
      setIsLoading(false);
    }
  };

  // handleKeyPress 函数：处理输入框的键盘事件，特别是回车键。
  const handleKeyPress = (e) => {
    // 如果按下的是Enter键且没有同时按住Shift键（防止换行），则发送消息。
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault(); // 阻止默认的回车换行行为
      handleSendMessage(); // 调用发送消息函数
    }
  };

  // JSX 渲染部分：构建聊天界面的UI。
  return (
    <div className="flex flex-col h-screen bg-gray-100">
      {/* 头部区域：显示应用标题和图标 */}
      <header className="bg-white shadow-sm border-b p-4 flex items-center justify-between">
        <Button variant="ghost" size="icon" onClick={() => navigate('/')}>
          <ArrowLeft className="h-6 w-6" />
        </Button>
        <div className="flex items-center justify-center flex-grow">
          <MessageCircle className="h-6 w-6 mr-2 text-blue-500" />
          <h1 className="text-xl font-bold text-gray-900">AI 医生咨询</h1>
        </div>
        <div className="w-12"></div>
      </header>

      {/* 主要内容区域：显示聊天消息，并支持滚动 */}
      <main className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* 遍历 messages 数组，渲染每一条聊天消息 */}
        {messages.map((msg, index) => (
          <div
            key={index} // 使用索引作为key，简单实现，实际应用中建议使用唯一ID
            className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`} // 根据发送者决定消息靠左或靠右
          >
            <Card
              className={`max-w-xl p-3 rounded-lg shadow-md ${
                msg.sender === 'user'
                  ? 'bg-blue-500 text-white' // 用户消息背景和文本颜色
                  : 'bg-white text-gray-800' // AI消息背景和文本颜色
              }`}
            >
              <CardContent className="p-0 text-sm">
                {msg.text} {/* 显示消息文本 */}
              </CardContent>
            </Card>
          </div>
        ))}
        {/* 加载指示器：当AI正在思考时显示 */}
        {isLoading && (
          <div className="flex justify-start">
            <Card className="max-w-xl p-3 rounded-lg shadow-md bg-white text-gray-800">
              <CardContent className="p-0 text-sm animate-pulse">
                AI 正在思考...
              </CardContent>
            </Card>
          </div>
        )}
        {/* 聊天区域底部引用：用于滚动到最新消息 */}
        <div ref={chatEndRef} />
      </main>

      {/* 底部输入区域：包含消息输入框和发送按钮 */}
      <div className="bg-white p-4 border-t flex items-center space-x-2">
        <Input
          placeholder="输入您的问题..." // 输入框的占位符
          value={inputMessage} // 绑定输入框的值到 inputMessage 状态
          onChange={(e) => setInputMessage(e.target.value)} // 处理输入变化，更新状态
          onKeyPress={handleKeyPress} // 监听键盘事件，用于回车发送
          className="flex-1" // 使输入框占据可用空间
          disabled={isLoading} // 当AI正在加载时禁用输入框
        />
        <Button onClick={handleSendMessage} disabled={isLoading}> {/* 发送按钮，当AI加载时禁用 */}
          <Send className="h-5 w-5" /> {/* 发送图标 */}
        </Button>
      </div>
    </div>
  );
}

export default AIChatPage; 