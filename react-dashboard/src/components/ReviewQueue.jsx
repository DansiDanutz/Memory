import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../config';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Alert, AlertDescription } from './ui/alert';
import { Checkbox } from './ui/checkbox';
import { Progress } from './ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { 
  CheckCircle, XCircle, Clock, FileText, MessageSquare, 
  Calendar, Image, Mic, Link, ChevronDown, ChevronUp,
  CheckSquare, Square, Info
} from 'lucide-react';

const ReviewQueue = ({ user }) => {
  const [memories, setMemories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [selectedMemories, setSelectedMemories] = useState(new Set());
  const [expandedMemory, setExpandedMemory] = useState(null);
  const [processingIds, setProcessingIds] = useState(new Set());
  const [stats, setStats] = useState({
    pending: 0,
    agreed: 0,
    notAgreed: 0
  });

  const sourceIcons = {
    chat_message: MessageSquare,
    email: FileText,
    calendar_event: Calendar,
    photo: Image,
    voice_message: Mic,
    web_clip: Link,
    document: FileText
  };

  useEffect(() => {
    fetchReviewQueue();
    fetchStats();
  }, [page]);

  const fetchReviewQueue = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page,
        per_page: 10
      });

      const response = await fetch(`${API_BASE_URL}/api/review/queue?${params}`, {
        credentials: 'include'
      });

      const data = await response.json();
      if (data.success) {
        setMemories(data.memories);
        setTotalPages(data.pagination.total_pages);
        setTotalCount(data.pagination.total);
      }
    } catch (error) {
      console.error('Error fetching review queue:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/stats`, {
        credentials: 'include'
      });

      const data = await response.json();
      if (data.success) {
        setStats({
          pending: data.stats.pending_memories,
          agreed: data.stats.agreed_memories,
          notAgreed: data.stats.total_memories - data.stats.agreed_memories - data.stats.pending_memories
        });
      }
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const handleAgree = async (memoryId) => {
    setProcessingIds(prev => new Set([...prev, memoryId]));
    try {
      const response = await fetch(`${API_BASE_URL}/api/review/${memoryId}/agree`, {
        method: 'POST',
        credentials: 'include'
      });

      const data = await response.json();
      if (data.success) {
        // Remove from list
        setMemories(prev => prev.filter(m => m.id !== memoryId));
        setSelectedMemories(prev => {
          const next = new Set(prev);
          next.delete(memoryId);
          return next;
        });
        
        // Update stats
        setStats(prev => ({
          ...prev,
          pending: prev.pending - 1,
          agreed: prev.agreed + 1
        }));
        
        setTotalCount(prev => prev - 1);
      }
    } catch (error) {
      console.error('Error marking memory as agreed:', error);
    } finally {
      setProcessingIds(prev => {
        const next = new Set(prev);
        next.delete(memoryId);
        return next;
      });
    }
  };

  const handleDisagree = async (memoryId) => {
    setProcessingIds(prev => new Set([...prev, memoryId]));
    try {
      const response = await fetch(`${API_BASE_URL}/api/review/${memoryId}/disagree`, {
        method: 'POST',
        credentials: 'include'
      });

      const data = await response.json();
      if (data.success) {
        // Remove from list
        setMemories(prev => prev.filter(m => m.id !== memoryId));
        setSelectedMemories(prev => {
          const next = new Set(prev);
          next.delete(memoryId);
          return next;
        });
        
        // Update stats
        setStats(prev => ({
          ...prev,
          pending: prev.pending - 1,
          notAgreed: prev.notAgreed + 1
        }));
        
        setTotalCount(prev => prev - 1);
      }
    } catch (error) {
      console.error('Error marking memory as not agreed:', error);
    } finally {
      setProcessingIds(prev => {
        const next = new Set(prev);
        next.delete(memoryId);
        return next;
      });
    }
  };

  const handleBulkAgree = async () => {
    for (const memoryId of selectedMemories) {
      await handleAgree(memoryId);
    }
  };

  const handleBulkDisagree = async () => {
    for (const memoryId of selectedMemories) {
      await handleDisagree(memoryId);
    }
  };

  const toggleSelectAll = () => {
    if (selectedMemories.size === memories.length) {
      setSelectedMemories(new Set());
    } else {
      setSelectedMemories(new Set(memories.map(m => m.id)));
    }
  };

  const toggleSelectMemory = (memoryId) => {
    setSelectedMemories(prev => {
      const next = new Set(prev);
      if (next.has(memoryId)) {
        next.delete(memoryId);
      } else {
        next.add(memoryId);
      }
      return next;
    });
  };

  const getQualityLabel = (score) => {
    if (score >= 0.8) return 'Excellent';
    if (score >= 0.6) return 'Good';
    if (score >= 0.4) return 'Fair';
    return 'Poor';
  };

  const getQualityColor = (score) => {
    if (score >= 0.8) return 'text-green-600';
    if (score >= 0.6) return 'text-blue-600';
    if (score >= 0.4) return 'text-yellow-600';
    return 'text-red-600';
  };

  const MemoryItem = ({ memory }) => {
    const SourceIcon = sourceIcons[memory.source_type] || FileText;
    const isExpanded = expandedMemory === memory.id;
    const isSelected = selectedMemories.has(memory.id);
    const isProcessing = processingIds.has(memory.id);

    return (
      <Card className={`mb-4 ${isSelected ? 'border-blue-500' : ''}`}>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-3">
              <Checkbox
                checked={isSelected}
                onCheckedChange={() => toggleSelectMemory(memory.id)}
                disabled={isProcessing}
              />
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <SourceIcon className="h-4 w-4 text-gray-500" />
                  <Badge variant="outline">{memory.source_type}</Badge>
                  <span className={`text-sm ${getQualityColor(memory.quality_score)}`}>
                    {getQualityLabel(memory.quality_score)} Quality
                  </span>
                </div>
                <p className={`text-sm ${isExpanded ? '' : 'line-clamp-3'}`}>
                  {memory.content}
                </p>
                {!isExpanded && memory.content.length > 200 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setExpandedMemory(memory.id)}
                    className="mt-2 p-0 h-auto text-blue-500"
                  >
                    <ChevronDown className="h-4 w-4 mr-1" />
                    Show more
                  </Button>
                )}
                {isExpanded && (
                  <>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setExpandedMemory(null)}
                      className="mt-2 p-0 h-auto text-blue-500"
                    >
                      <ChevronUp className="h-4 w-4 mr-1" />
                      Show less
                    </Button>
                    
                    {memory.tags && memory.tags.length > 0 && (
                      <div className="mt-3">
                        <span className="text-xs text-gray-500">Tags:</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {memory.tags.map((tag, idx) => (
                            <Badge key={idx} variant="secondary" className="text-xs">
                              {tag}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {memory.participants && memory.participants.length > 0 && (
                      <div className="mt-2 text-xs text-gray-500">
                        Participants: {memory.participants.join(', ')}
                      </div>
                    )}
                    
                    {memory.metadata && Object.keys(memory.metadata).length > 0 && (
                      <div className="mt-2 p-2 bg-gray-50 rounded text-xs">
                        <span className="font-semibold">Metadata:</span>
                        <pre className="mt-1">{JSON.stringify(memory.metadata, null, 2)}</pre>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
            <div className="flex flex-col gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleAgree(memory.id)}
                disabled={isProcessing}
                className="text-green-600 hover:bg-green-50"
              >
                <CheckCircle className="h-4 w-4 mr-1" />
                Agree
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleDisagree(memory.id)}
                disabled={isProcessing}
                className="text-red-600 hover:bg-red-50"
              >
                <XCircle className="h-4 w-4 mr-1" />
                Disagree
              </Button>
            </div>
          </div>
          <div className="flex items-center gap-4 mt-3 text-xs text-gray-400">
            <span>{new Date(memory.created_at).toLocaleString()}</span>
            <span>Quality: {Math.round(memory.quality_score * 100)}%</span>
          </div>
        </CardHeader>
      </Card>
    );
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Memory Review Queue</h1>
        <p className="text-gray-600">
          Review and approve memories before they're permanently stored
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Pending Review</p>
                <p className="text-2xl font-bold text-orange-600">{stats.pending}</p>
              </div>
              <Clock className="h-8 w-8 text-orange-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Agreed</p>
                <p className="text-2xl font-bold text-green-600">{stats.agreed}</p>
              </div>
              <CheckCircle className="h-8 w-8 text-green-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Not Agreed</p>
                <p className="text-2xl font-bold text-red-600">{stats.notAgreed}</p>
              </div>
              <XCircle className="h-8 w-8 text-red-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Agreement Rate</p>
                <p className="text-2xl font-bold">
                  {stats.agreed + stats.notAgreed > 0
                    ? Math.round((stats.agreed / (stats.agreed + stats.notAgreed)) * 100)
                    : 0}%
                </p>
              </div>
            </div>
            <Progress 
              value={stats.agreed + stats.notAgreed > 0
                ? (stats.agreed / (stats.agreed + stats.notAgreed)) * 100
                : 0} 
              className="mt-2"
            />
          </CardContent>
        </Card>
      </div>

      {selectedMemories.size > 0 && (
        <div className="mb-4 p-4 bg-blue-50 rounded-lg flex items-center justify-between">
          <span className="text-sm">
            {selectedMemories.size} memories selected
          </span>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="default"
              onClick={handleBulkAgree}
              className="bg-green-600 hover:bg-green-700"
            >
              <CheckCircle className="h-4 w-4 mr-1" />
              Agree Selected
            </Button>
            <Button
              size="sm"
              variant="default"
              onClick={handleBulkDisagree}
              className="bg-red-600 hover:bg-red-700"
            >
              <XCircle className="h-4 w-4 mr-1" />
              Disagree Selected
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setSelectedMemories(new Set())}
            >
              Clear Selection
            </Button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      ) : memories.length === 0 ? (
        <Alert>
          <CheckCircle className="h-4 w-4" />
          <AlertDescription>
            No memories pending review. Great job staying on top of your review queue!
          </AlertDescription>
        </Alert>
      ) : (
        <>
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Checkbox
                checked={selectedMemories.size === memories.length && memories.length > 0}
                onCheckedChange={toggleSelectAll}
              />
              <span className="text-sm text-gray-600">Select all</span>
            </div>
            <span className="text-sm text-gray-500">
              Showing {memories.length} of {totalCount} pending memories
            </span>
          </div>

          <div>
            {memories.map((memory) => (
              <MemoryItem key={memory.id} memory={memory} />
            ))}
          </div>

          {totalPages > 1 && (
            <div className="mt-6 flex justify-center gap-2">
              <Button
                variant="outline"
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                Previous
              </Button>
              <span className="flex items-center px-4">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="outline"
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default ReviewQueue;