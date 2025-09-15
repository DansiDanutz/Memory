import React, { useState, useEffect, useRef } from 'react';
import { API_BASE_URL } from '../config';

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
  const [pendingCount, setPendingCount] = useState(0);
  const [filterStatus, setFilterStatus] = useState('all'); // all, agreed, not_agreed, pending
  const [showReviewMode, setShowReviewMode] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Load pending memories on mount
    fetchPendingMemories();
  }, []);

  const fetchPendingMemories = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/memory/pending`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include'
      });

      const data = await response.json();
      if (data.success) {
        setPendingCount(data.count || 0);
        
        // Add pending memories to messages if in review mode
        if (showReviewMode && data.memories && data.memories.length > 0) {
          const pendingMessages = data.memories.map(memory => ({
            id: memory.id,
            type: 'memory',
            content: memory.content,
            timestamp: new Date(memory.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            tag: memory.tag,
            agreementStatus: 'pending'
          }));
          setMessages(prev => [...prev, ...pendingMessages]);
        }
      }
    } catch (error) {
      console.error('Error fetching pending memories:', error);
    }
  };

  const handleMarkAgreed = async (messageId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/memory/agree`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ memory_id: messageId })
      });

      const data = await response.json();
      if (data.success) {
        // Update message status in UI
        setMessages(prev => prev.map(msg => 
          msg.id === messageId 
            ? { ...msg, agreementStatus: 'agreed' }
            : msg
        ));
        
        // Update pending count
        setPendingCount(prev => Math.max(0, prev - 1));
        
        // Show success feedback
        const feedbackMessage = {
          id: Date.now(),
          type: 'system',
          content: '✅ Memory marked as agreed',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };
        setMessages(prev => [...prev, feedbackMessage]);
      }
    } catch (error) {
      console.error('Error marking memory as agreed:', error);
    }
  };

  const handleMarkNotAgreed = async (messageId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/memory/disagree`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ memory_id: messageId })
      });

      const data = await response.json();
      if (data.success) {
        // Update message status in UI
        setMessages(prev => prev.map(msg => 
          msg.id === messageId 
            ? { ...msg, agreementStatus: 'not_agreed' }
            : msg
        ));
        
        // Update pending count
        setPendingCount(prev => Math.max(0, prev - 1));
        
        // Show success feedback
        const feedbackMessage = {
          id: Date.now(),
          type: 'system',
          content: '❌ Memory marked as not agreed',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };
        setMessages(prev => [...prev, feedbackMessage]);
      }
    } catch (error) {
      console.error('Error marking memory as not agreed:', error);
    }
  };

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

    try {
      // Send to real API
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ message: inputMessage })
      });

      const data = await response.json();

      if (data.success) {
        // Add classification info to user message if available
        if (data.classification) {
          const updatedUserMessage = {
            ...userMessage,
            classification: data.classification,
            agreementStatus: 'pending'
          };
          setMessages(prev => {
            const newMessages = [...prev];
            const lastIndex = newMessages.findIndex(msg => msg.id === userMessage.id);
            if (lastIndex !== -1) {
              newMessages[lastIndex] = updatedUserMessage;
            }
            return newMessages;
          });
        }

        // Add assistant response
        const assistantMessage = {
          id: Date.now() + 1,
          type: 'assistant',
          content: data.response || `I've saved that memory for you! 📝 I've classified it as ${data.classification?.tag || 'a general memory'} that you can easily retrieve later.`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          tag: data.classification?.tag
        };

        setMessages(prev => [...prev, assistantMessage]);
      } else {
        // Handle error
        const errorMessage = {
          id: Date.now() + 1,
          type: 'assistant',
          content: 'Sorry, I encountered an error while processing your message. Please try again.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        id: Date.now() + 1,
        type: 'assistant',
        content: 'I apologize, but I\'m having trouble connecting to the server. Please check your connection and try again.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  const quickActions = [
    { icon: '📝', text: 'Add Memory', action: () => setInputMessage('I want to remember that ') },
    { icon: '🔍', text: 'Search', action: () => setInputMessage('Find memories about ') },
    { icon: '📊', text: 'Daily Summary', action: () => setInputMessage('Show me my daily summary') },
    { icon: '🔒', text: 'Private Note', action: () => setInputMessage('Save this privately: ') },
    { icon: '📋', text: `Review (${pendingCount})`, action: () => { setShowReviewMode(!showReviewMode); fetchPendingMemories(); } }
  ];

  const getTagColor = (tag) => {
    switch(tag) {
      case 'confidential':
        return '#FFA500';
      case 'secret':
        return '#FF6B6B';
      case 'ultrasecret':
        return '#FF0000';
      case 'chronological':
        return '#4CAF50';
      default:
        return '#2196F3';
    }
  };

  const getTagIcon = (tag) => {
    switch(tag) {
      case 'confidential':
        return '🔒';
      case 'secret':
        return '🔐';
      case 'ultrasecret':
        return '🛡️';
      case 'chronological':
        return '📅';
      default:
        return '📝';
    }
  };

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

          {/* Filter Bar for Review Mode */}
          {showReviewMode && (
            <div style={{
              padding: '0.75rem',
              background: 'rgba(255, 255, 255, 0.1)',
              borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
              display: 'flex',
              gap: '0.5rem',
              alignItems: 'center'
            }}>
              <span style={{ color: 'white', fontSize: '0.9rem', marginRight: '1rem' }}>Filter:</span>
              {['all', 'pending', 'agreed', 'not_agreed'].map(status => (
                <button
                  key={status}
                  onClick={() => setFilterStatus(status)}
                  style={{
                    padding: '0.5rem 1rem',
                    borderRadius: '20px',
                    border: 'none',
                    background: filterStatus === status ? '#25D366' : 'rgba(255, 255, 255, 0.2)',
                    color: 'white',
                    cursor: 'pointer',
                    fontSize: '0.85rem',
                    textTransform: 'capitalize'
                  }}
                >
                  {status.replace('_', ' ')}
                </button>
              ))}
            </div>
          )}

          {/* Messages Area */}
          <div style={{
            flex: 1,
            overflowY: 'auto',
            padding: '1rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '1rem',
            background: 'rgba(255, 255, 255, 0.05)',
            height: 'calc(100% - 200px)'
          }}>
            {messages
              .filter(msg => {
                if (!showReviewMode || filterStatus === 'all') return true;
                if (filterStatus === 'pending') return msg.agreementStatus === 'pending';
                if (filterStatus === 'agreed') return msg.agreementStatus === 'agreed';
                if (filterStatus === 'not_agreed') return msg.agreementStatus === 'not_agreed';
                return true;
              })
              .map((message) => (
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
                      ? message.agreementStatus === 'agreed' 
                        ? 'rgba(76, 175, 80, 0.9)'
                        : message.agreementStatus === 'not_agreed'
                        ? 'rgba(244, 67, 54, 0.9)'
                        : 'rgba(37, 211, 102, 0.9)'
                      : message.type === 'system'
                      ? 'rgba(255, 152, 0, 0.3)'
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
                  
                  {/* Agreement Status Badge */}
                  {message.agreementStatus && (
                    <div style={{
                      marginBottom: '0.5rem',
                      display: 'inline-block',
                      padding: '0.25rem 0.5rem',
                      borderRadius: '12px',
                      fontSize: '0.7rem',
                      fontWeight: '600',
                      background: 
                        message.agreementStatus === 'agreed' ? '#4CAF50' :
                        message.agreementStatus === 'not_agreed' ? '#F44336' :
                        '#FFA500',
                      color: 'white'
                    }}>
                      {message.agreementStatus === 'agreed' ? '✅ Agreed' :
                       message.agreementStatus === 'not_agreed' ? '❌ Not Agreed' :
                       '⏳ Pending'}
                    </div>
                  )}
                  
                  {/* Agreement Buttons for Pending Memories */}
                  {message.agreementStatus === 'pending' && showReviewMode && (
                    <div style={{
                      marginTop: '0.75rem',
                      paddingTop: '0.75rem',
                      borderTop: '1px solid rgba(255, 255, 255, 0.2)',
                      display: 'flex',
                      gap: '0.5rem',
                      justifyContent: 'center'
                    }}>
                      <button
                        onClick={() => handleMarkAgreed(message.id)}
                        style={{
                          padding: '0.5rem 1rem',
                          borderRadius: '20px',
                          border: 'none',
                          background: '#4CAF50',
                          color: 'white',
                          cursor: 'pointer',
                          fontSize: '0.85rem',
                          fontWeight: '600',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.25rem'
                        }}
                        onMouseEnter={(e) => e.target.style.transform = 'scale(1.05)'}
                        onMouseLeave={(e) => e.target.style.transform = 'scale(1)'}
                      >
                        ✅ Agree
                      </button>
                      <button
                        onClick={() => handleMarkNotAgreed(message.id)}
                        style={{
                          padding: '0.5rem 1rem',
                          borderRadius: '20px',
                          border: 'none',
                          background: '#F44336',
                          color: 'white',
                          cursor: 'pointer',
                          fontSize: '0.85rem',
                          fontWeight: '600',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.25rem'
                        }}
                        onMouseEnter={(e) => e.target.style.transform = 'scale(1.05)'}
                        onMouseLeave={(e) => e.target.style.transform = 'scale(1)'}
                      >
                        ❌ Not Agree
                      </button>
                    </div>
                  )}
                  
                  {/* Show classification for user messages */}
                  {message.classification && (
                    <div style={{
                      marginTop: '0.5rem',
                      paddingTop: '0.5rem',
                      borderTop: '1px solid rgba(255, 255, 255, 0.2)',
                      fontSize: '0.75rem',
                      color: 'rgba(255, 255, 255, 0.9)'
                    }}>
                      <span style={{ marginRight: '0.25rem' }}>
                        {getTagIcon(message.classification.tag)}
                      </span>
                      Classified as: {message.classification.tag}
                      {message.classification.confidence && (
                        <span style={{ marginLeft: '0.5rem', color: 'rgba(255, 255, 255, 0.7)' }}>
                          ({message.classification.confidence})
                        </span>
                      )}
                    </div>
                  )}

                  {/* Show tag for assistant messages */}
                  {message.tag && (
                    <div style={{
                      marginTop: '0.5rem',
                      display: 'inline-block',
                      padding: '0.25rem 0.5rem',
                      background: getTagColor(message.tag),
                      borderRadius: '12px',
                      fontSize: '0.7rem'
                    }}>
                      {getTagIcon(message.tag)} {message.tag}
                    </div>
                  )}

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

    </div>
  );
};

export default Dashboard;