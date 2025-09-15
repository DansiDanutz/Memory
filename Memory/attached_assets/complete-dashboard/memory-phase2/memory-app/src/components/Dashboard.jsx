import React, { useState, useEffect, useRef } from 'react';

const Dashboard = ({ user, onLogout }) => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'assistant',
      content: `Hello ${user?.name || 'there'}! 👋 I'm your Memory Assistant. I'm here to help you capture, organize, and recall your life's moments. What would you like to remember today?`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [showMenu, setShowMenu] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim()) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: inputMessage,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsTyping(true);

    // Simulate AI response
    setTimeout(() => {
      const responses = [
        "I've saved that memory for you! 📝 I've classified it as a general memory that you can easily retrieve later.",
        "That's interesting! I've added this to your chronological timeline. Would you like me to set a reminder about this?",
        "I understand this is important to you. I've stored this securely in your confidential memories. 🔒",
        "Great memory! I've organized this with your other experiences. I can help you find patterns in your memories if you'd like.",
        "I've captured that moment for you! Your memories are building a beautiful story of your life. ✨"
      ];

      const assistantMessage = {
        id: Date.now() + 1,
        type: 'assistant',
        content: responses[Math.floor(Math.random() * responses.length)],
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setMessages(prev => [...prev, assistantMessage]);
      setIsTyping(false);
    }, 1500);
  };

  const quickActions = [
    { icon: '📝', text: 'Add Memory', action: () => setInputMessage('I want to remember that ') },
    { icon: '🔍', text: 'Search', action: () => setInputMessage('Find memories about ') },
    { icon: '📊', text: 'Daily Summary', action: () => setInputMessage('Show me my daily summary') },
    { icon: '🔒', text: 'Private Note', action: () => setInputMessage('Save this privately: ') }
  ];

  return (
    <div className="app-container">
      <div className="phone-mockup">
        <div className="phone-content" style={{ padding: 0, height: '100%' }}>
          {/* Chat Header */}
          <div style={{
            background: 'rgba(255, 255, 255, 0.15)',
            backdropFilter: 'blur(20px)',
            WebkitBackdropFilter: 'blur(20px)',
            borderBottom: '1px solid rgba(255, 255, 255, 0.2)',
            padding: '1rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            position: 'sticky',
            top: 0,
            zIndex: 10
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <div style={{
                width: '40px',
                height: '40px',
                background: 'linear-gradient(135deg, #25D366 0%, #128C7E 100%)',
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '1.2rem'
              }}>
                🧠
              </div>
              <div>
                <div style={{ color: 'white', fontWeight: '600', fontSize: '1rem' }}>
                  Memory Assistant
                </div>
                <div style={{ color: 'rgba(255, 255, 255, 0.7)', fontSize: '0.8rem' }}>
                  {isTyping ? 'typing...' : 'online'}
                </div>
              </div>
            </div>
            
            <div style={{ position: 'relative' }}>
              <button
                onClick={() => setShowMenu(!showMenu)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'white',
                  fontSize: '1.2rem',
                  cursor: 'pointer',
                  padding: '0.5rem'
                }}
              >
                ⋮
              </button>
              
              {showMenu && (
                <div style={{
                  position: 'absolute',
                  top: '100%',
                  right: 0,
                  background: 'rgba(255, 255, 255, 0.95)',
                  backdropFilter: 'blur(20px)',
                  borderRadius: '8px',
                  padding: '0.5rem',
                  minWidth: '150px',
                  boxShadow: '0 4px 20px rgba(0, 0, 0, 0.2)',
                  zIndex: 20
                }}>
                  <button
                    onClick={() => {
                      setShowMenu(false);
                      // Add settings functionality
                    }}
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      background: 'none',
                      border: 'none',
                      textAlign: 'left',
                      cursor: 'pointer',
                      borderRadius: '4px',
                      color: '#333'
                    }}
                  >
                    ⚙️ Settings
                  </button>
                  <button
                    onClick={() => {
                      setShowMenu(false);
                      onLogout();
                    }}
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      background: 'none',
                      border: 'none',
                      textAlign: 'left',
                      cursor: 'pointer',
                      borderRadius: '4px',
                      color: '#333'
                    }}
                  >
                    🚪 Logout
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Messages Area */}
          <div style={{
            flex: 1,
            overflowY: 'auto',
            padding: '1rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '1rem',
            background: 'rgba(255, 255, 255, 0.05)'
          }}>
            {messages.map((message) => (
              <div
                key={message.id}
                style={{
                  display: 'flex',
                  justifyContent: message.type === 'user' ? 'flex-end' : 'flex-start'
                }}
              >
                <div
                  style={{
                    maxWidth: '75%',
                    padding: '0.75rem 1rem',
                    borderRadius: '18px',
                    background: message.type === 'user' 
                      ? 'rgba(37, 211, 102, 0.9)' 
                      : 'rgba(255, 255, 255, 0.15)',
                    backdropFilter: 'blur(10px)',
                    WebkitBackdropFilter: 'blur(10px)',
                    color: 'white',
                    fontSize: '0.9rem',
                    lineHeight: '1.4',
                    border: message.type === 'assistant' ? '1px solid rgba(255, 255, 255, 0.2)' : 'none',
                    borderBottomRightRadius: message.type === 'user' ? '4px' : '18px',
                    borderBottomLeftRadius: message.type === 'assistant' ? '4px' : '18px',
                    wordWrap: 'break-word'
                  }}
                >
                  <div>{message.content}</div>
                  <div style={{
                    fontSize: '0.7rem',
                    color: 'rgba(255, 255, 255, 0.7)',
                    textAlign: 'right',
                    marginTop: '0.25rem'
                  }}>
                    {message.timestamp}
                  </div>
                </div>
              </div>
            ))}
            
            {isTyping && (
              <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                <div style={{
                  padding: '0.75rem 1rem',
                  borderRadius: '18px',
                  borderBottomLeftRadius: '4px',
                  background: 'rgba(255, 255, 255, 0.15)',
                  backdropFilter: 'blur(10px)',
                  WebkitBackdropFilter: 'blur(10px)',
                  border: '1px solid rgba(255, 255, 255, 0.2)',
                  color: 'white'
                }}>
                  <div style={{ display: 'flex', gap: '0.25rem', alignItems: 'center' }}>
                    <div className="typing-dot" style={{ 
                      width: '6px', 
                      height: '6px', 
                      background: 'rgba(255, 255, 255, 0.7)', 
                      borderRadius: '50%',
                      animation: 'typing 1.4s infinite ease-in-out'
                    }}></div>
                    <div className="typing-dot" style={{ 
                      width: '6px', 
                      height: '6px', 
                      background: 'rgba(255, 255, 255, 0.7)', 
                      borderRadius: '50%',
                      animation: 'typing 1.4s infinite ease-in-out 0.2s'
                    }}></div>
                    <div className="typing-dot" style={{ 
                      width: '6px', 
                      height: '6px', 
                      background: 'rgba(255, 255, 255, 0.7)', 
                      borderRadius: '50%',
                      animation: 'typing 1.4s infinite ease-in-out 0.4s'
                    }}></div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Actions */}
          <div style={{
            padding: '0.5rem 1rem',
            background: 'rgba(255, 255, 255, 0.1)',
            borderTop: '1px solid rgba(255, 255, 255, 0.1)'
          }}>
            <div style={{
              display: 'flex',
              gap: '0.5rem',
              overflowX: 'auto',
              paddingBottom: '0.5rem'
            }}>
              {quickActions.map((action, index) => (
                <button
                  key={index}
                  onClick={action.action}
                  style={{
                    background: 'rgba(255, 255, 255, 0.1)',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    borderRadius: '20px',
                    padding: '0.5rem 0.75rem',
                    color: 'white',
                    fontSize: '0.8rem',
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.25rem',
                    transition: 'all 0.3s ease'
                  }}
                  onMouseEnter={(e) => {
                    e.target.style.background = 'rgba(255, 255, 255, 0.2)';
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.background = 'rgba(255, 255, 255, 0.1)';
                  }}
                >
                  <span>{action.icon}</span>
                  <span>{action.text}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Input Area */}
          <form onSubmit={handleSendMessage} style={{
            background: 'rgba(255, 255, 255, 0.15)',
            backdropFilter: 'blur(20px)',
            WebkitBackdropFilter: 'blur(20px)',
            borderTop: '1px solid rgba(255, 255, 255, 0.2)',
            padding: '1rem',
            display: 'flex',
            gap: '0.75rem',
            alignItems: 'center'
          }}>
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="Type your memory or question..."
              style={{
                flex: 1,
                padding: '0.75rem 1rem',
                background: 'rgba(255, 255, 255, 0.1)',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                borderRadius: '25px',
                color: 'white',
                fontSize: '0.9rem',
                backdropFilter: 'blur(10px)',
                WebkitBackdropFilter: 'blur(10px)',
                outline: 'none'
              }}
              onFocus={(e) => {
                e.target.style.background = 'rgba(255, 255, 255, 0.15)';
                e.target.style.borderColor = 'rgba(255, 255, 255, 0.4)';
              }}
              onBlur={(e) => {
                e.target.style.background = 'rgba(255, 255, 255, 0.1)';
                e.target.style.borderColor = 'rgba(255, 255, 255, 0.2)';
              }}
            />
            <button
              type="submit"
              disabled={!inputMessage.trim()}
              style={{
                background: inputMessage.trim() 
                  ? 'linear-gradient(135deg, #25D366 0%, #128C7E 100%)' 
                  : 'rgba(255, 255, 255, 0.2)',
                border: 'none',
                borderRadius: '50%',
                width: '45px',
                height: '45px',
                color: 'white',
                cursor: inputMessage.trim() ? 'pointer' : 'not-allowed',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '1.2rem',
                transition: 'all 0.3s ease',
                boxShadow: inputMessage.trim() ? '0 4px 15px rgba(0, 0, 0, 0.2)' : 'none'
              }}
            >
              ➤
            </button>
          </form>
        </div>
      </div>

      <style jsx>{`
        @keyframes typing {
          0%, 60%, 100% {
            transform: translateY(0);
            opacity: 0.4;
          }
          30% {
            transform: translateY(-10px);
            opacity: 1;
          }
        }
      `}</style>
    </div>
  );
};

export default Dashboard;

