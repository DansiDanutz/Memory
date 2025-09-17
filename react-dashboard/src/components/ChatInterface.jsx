import React, { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button.jsx';
import { Input } from '@/components/ui/input.jsx';
import { Avatar, AvatarFallback } from '@/components/ui/avatar.jsx';
import { 
  Send, 
  Search, 
  MoreVertical, 
  Brain, 
  User, 
  Clock, 
  Tag, 
  Shield,
  Lock,
  Eye,
  Settings,
  LogOut
} from 'lucide-react';
import { Badge } from '@/components/ui/badge.jsx';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu.jsx';

const ChatInterface = ({ user, onLogout }) => {
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [showSearch, setShowSearch] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    loadMemories();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadMemories = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/memories', {
        credentials: 'include'
      });
      const data = await response.json();
      
      if (data.success) {
        setMessages(data.messages);
      }
    } catch (err) {
      console.error('Failed to load memories:', err);
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || loading) return;

    const userMessage = {
      id: `temp_${Date.now()}`,
      content: newMessage,
      timestamp: new Date().toISOString(),
      type: 'user_message',
      sender: 'user'
    };

    setMessages(prev => [...prev, userMessage]);
    setNewMessage('');
    setLoading(true);

    try {
      const response = await fetch('http://localhost:5000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ message: newMessage })
      });

      const data = await response.json();

      if (data.success) {
        // Add Aria's response
        const ariaMessage = {
          id: `aria_${Date.now()}`,
          content: data.response,
          timestamp: new Date().toISOString(),
          type: 'ai_message',
          sender: 'agent',
          assistant_name: data.assistant_name || 'Aria'
        };
        
        setMessages(prev => [...prev, ariaMessage]);
      }
    } catch (err) {
      console.error('Failed to send message:', err);
    } finally {
      setLoading(false);
    }
  };

  const searchMemories = async () => {
    if (!searchQuery.trim()) return;

    try {
      const response = await fetch('http://localhost:5000/api/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ query: searchQuery })
      });

      const data = await response.json();

      if (data.success) {
        setMessages(data.messages);
      }
    } catch (err) {
      console.error('Search failed:', err);
    }
  };

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffInHours = (now - date) / (1000 * 60 * 60);

    if (diffInHours < 24) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (diffInHours < 48) {
      return 'Yesterday';
    } else {
      return date.toLocaleDateString();
    }
  };

  const getTagColor = (tag) => {
    const colors = {
      '#general': 'bg-blue-100 text-blue-800',
      '#chronological': 'bg-green-100 text-green-800',
      '#confidential': 'bg-yellow-100 text-yellow-800',
      '#secret': 'bg-orange-100 text-orange-800',
      '#ultrasecret': 'bg-red-100 text-red-800'
    };
    return colors[tag] || 'bg-gray-100 text-gray-800';
  };

  const getTagIcon = (tag) => {
    switch (tag) {
      case '#confidential':
        return <Shield className="w-3 h-3" />;
      case '#secret':
        return <Lock className="w-3 h-3" />;
      case '#ultrasecret':
        return <Eye className="w-3 h-3" />;
      case '#chronological':
        return <Clock className="w-3 h-3" />;
      default:
        return <Tag className="w-3 h-3" />;
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-green-500 text-white p-4 flex items-center justify-between shadow-lg">
        <div className="flex items-center space-x-3">
          <Avatar className="w-10 h-10">
            <AvatarFallback className="bg-green-600 text-white">
              <Brain className="w-5 h-5" />
            </AvatarFallback>
          </Avatar>
          <div>
            <h1 className="font-semibold">Aria</h1>
            <p className="text-xs text-green-100">Your Personal Memory Assistant</p>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowSearch(!showSearch)}
            className="text-white hover:bg-green-600"
          >
            <Search className="w-5 h-5" />
          </Button>
          
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm" className="text-white hover:bg-green-600">
                <MoreVertical className="w-5 h-5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem>
                <Settings className="w-4 h-4 mr-2" />
                Settings
              </DropdownMenuItem>
              <DropdownMenuItem onClick={onLogout}>
                <LogOut className="w-4 h-4 mr-2" />
                Logout
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Search Bar */}
      {showSearch && (
        <div className="bg-white border-b p-4">
          <div className="flex space-x-2">
            <Input
              placeholder="Search your memories..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && searchMemories()}
              className="flex-1"
            />
            <Button onClick={searchMemories} size="sm">
              <Search className="w-4 h-4" />
            </Button>
            <Button 
              onClick={() => {
                setSearchQuery('');
                setShowSearch(false);
                loadMemories();
              }} 
              variant="outline" 
              size="sm"
            >
              Clear
            </Button>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center py-12">
            <Brain className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-600 mb-2">Welcome! I'm Aria</h3>
            <p className="text-gray-500">Your personal memory assistant. I'm here to help you store and organize your thoughts, memories, and important moments. Start by saying hello!</p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className="flex items-start space-x-2 max-w-xs lg:max-w-md">
                {message.sender === 'agent' && (
                  <Avatar className="w-8 h-8 mt-1">
                    <AvatarFallback className="bg-green-500 text-white">
                      <Brain className="w-4 h-4" />
                    </AvatarFallback>
                  </Avatar>
                )}
                
                <div
                  className={`rounded-lg p-3 ${
                    message.sender === 'user'
                      ? 'bg-green-500 text-white'
                      : 'bg-white border shadow-sm'
                  }`}
                >
                  <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                  
                  {/* Message metadata */}
                  <div className="flex items-center justify-between mt-2 space-x-2">
                    <div className="flex items-center space-x-1">
                      {message.tag && (
                        <Badge 
                          variant="secondary" 
                          className={`text-xs ${getTagColor(message.tag)}`}
                        >
                          {getTagIcon(message.tag)}
                          <span className="ml-1">{message.tag.replace('#', '')}</span>
                        </Badge>
                      )}
                    </div>
                    
                    <span 
                      className={`text-xs ${
                        message.sender === 'user' ? 'text-green-100' : 'text-gray-500'
                      }`}
                    >
                      {formatTime(message.timestamp)}
                    </span>
                  </div>

                  {/* Classification info for user messages */}
                  {message.classification && (
                    <div className="mt-2 pt-2 border-t border-green-400">
                      <p className="text-xs text-green-100">
                        Classified as: {message.classification.tag} 
                        ({message.classification.confidence})
                      </p>
                    </div>
                  )}
                </div>

                {message.sender === 'user' && (
                  <Avatar className="w-8 h-8 mt-1">
                    <AvatarFallback className="bg-gray-500 text-white">
                      <User className="w-4 h-4" />
                    </AvatarFallback>
                  </Avatar>
                )}
              </div>
            </div>
          ))
        )}
        
        {loading && (
          <div className="flex justify-start">
            <div className="flex items-start space-x-2">
              <Avatar className="w-8 h-8">
                <AvatarFallback className="bg-green-500 text-white">
                  <Brain className="w-4 h-4" />
                </AvatarFallback>
              </Avatar>
              <div className="bg-white border rounded-lg p-3">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Message Input */}
      <div className="bg-white border-t p-4">
        <form onSubmit={sendMessage} className="flex space-x-2">
          <Input
            placeholder="Type a message to your Memory Assistant..."
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            disabled={loading}
            className="flex-1"
          />
          <Button 
            type="submit" 
            disabled={loading || !newMessage.trim()}
            className="bg-green-500 hover:bg-green-600"
          >
            <Send className="w-4 h-4" />
          </Button>
        </form>
        
        <div className="mt-2 text-center">
          <p className="text-xs text-gray-500">
            Your messages are automatically classified and securely stored
          </p>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;

