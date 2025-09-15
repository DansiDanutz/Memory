import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../config';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Alert, AlertDescription } from './ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { 
  Lightbulb, TrendingUp, Target, CheckCircle, AlertCircle, 
  Info, Star, ChevronRight, Eye, EyeOff, ThumbsUp 
} from 'lucide-react';

const InsightsPage = ({ user }) => {
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedType, setSelectedType] = useState('all');
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [selectedInsight, setSelectedInsight] = useState(null);
  const [stats, setStats] = useState({
    total: 0,
    unread: 0,
    actionTaken: 0
  });

  const insightTypes = {
    pattern_based: { icon: TrendingUp, color: 'blue', label: 'Pattern-Based' },
    behavioral: { icon: Target, color: 'green', label: 'Behavioral' },
    recommendation: { icon: Lightbulb, color: 'yellow', label: 'Recommendation' },
    alert: { icon: AlertCircle, color: 'red', label: 'Alert' },
    achievement: { icon: Star, color: 'purple', label: 'Achievement' }
  };

  useEffect(() => {
    fetchInsights();
    fetchStats();
  }, [selectedType, unreadOnly, page]);

  const fetchInsights = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page,
        per_page: 9,
        ...(selectedType !== 'all' && { insight_type: selectedType }),
        unread_only: unreadOnly
      });

      const response = await fetch(`${API_BASE_URL}/api/insights?${params}`, {
        credentials: 'include'
      });

      const data = await response.json();
      if (data.success) {
        setInsights(data.insights);
        setTotalPages(data.pagination.total_pages);
      }
    } catch (error) {
      console.error('Error fetching insights:', error);
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
          total: data.stats.total_insights,
          unread: data.stats.unread_insights,
          actionTaken: 0 // Would need backend support
        });
      }
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const markAsRead = async (insightId) => {
    // This would need a backend endpoint
    console.log('Marking as read:', insightId);
    fetchInsights();
  };

  const markActionTaken = async (insightId) => {
    // This would need a backend endpoint
    console.log('Marking action taken:', insightId);
    fetchInsights();
  };

  const getConfidenceLabel = (confidence) => {
    if (confidence >= 0.9) return 'Very High';
    if (confidence >= 0.75) return 'High';
    if (confidence >= 0.5) return 'Medium';
    return 'Low';
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.9) return 'text-green-600';
    if (confidence >= 0.75) return 'text-blue-600';
    if (confidence >= 0.5) return 'text-yellow-600';
    return 'text-gray-600';
  };

  const getImpactLabel = (impact) => {
    if (impact >= 0.8) return 'High Impact';
    if (impact >= 0.5) return 'Medium Impact';
    return 'Low Impact';
  };

  const InsightCard = ({ insight }) => {
    const typeInfo = insightTypes[insight.type] || insightTypes.pattern_based;
    const Icon = typeInfo.icon;

    return (
      <Card 
        className={`hover:shadow-lg transition-shadow cursor-pointer ${
          !insight.is_read ? 'border-l-4 border-blue-500' : ''
        }`}
        onClick={() => setSelectedInsight(insight)}
      >
        <CardHeader>
          <div className="flex justify-between items-start">
            <div className="flex items-center gap-2">
              <Icon className={`h-5 w-5 text-${typeInfo.color}-500`} />
              <Badge variant="secondary">{typeInfo.label}</Badge>
            </div>
            {!insight.is_read && (
              <Badge variant="default" className="bg-blue-500">New</Badge>
            )}
          </div>
          <CardTitle className="text-lg mt-2">{insight.title}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-700 mb-3 line-clamp-3">
            {insight.description}
          </p>
          
          <div className="flex items-center justify-between mb-3">
            <span className={`text-sm font-semibold ${getConfidenceColor(insight.confidence)}`}>
              {getConfidenceLabel(insight.confidence)} Confidence
            </span>
            <Badge variant="outline" className="text-xs">
              {getImpactLabel(insight.impact_score)}
            </Badge>
          </div>

          {insight.recommendations && insight.recommendations.length > 0 && (
            <div className="mb-3">
              <p className="text-xs text-gray-500 mb-1">Recommendations:</p>
              <ul className="text-xs space-y-1">
                {insight.recommendations.slice(0, 2).map((rec, idx) => (
                  <li key={idx} className="flex items-start gap-1">
                    <ChevronRight className="h-3 w-3 mt-0.5 flex-shrink-0" />
                    <span className="line-clamp-1">{rec}</span>
                  </li>
                ))}
                {insight.recommendations.length > 2 && (
                  <li className="text-gray-400">
                    +{insight.recommendations.length - 2} more...
                  </li>
                )}
              </ul>
            </div>
          )}

          <div className="flex items-center justify-between text-xs text-gray-400">
            <span>{new Date(insight.created_at).toLocaleDateString()}</span>
            <div className="flex items-center gap-2">
              {insight.is_read ? (
                <Eye className="h-3 w-3" />
              ) : (
                <EyeOff className="h-3 w-3" />
              )}
              {insight.action_taken && (
                <CheckCircle className="h-3 w-3 text-green-500" />
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    );
  };

  const InsightDetail = ({ insight }) => {
    const typeInfo = insightTypes[insight.type] || insightTypes.pattern_based;
    const Icon = typeInfo.icon;

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
        <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
          <div className="p-6">
            <div className="flex justify-between items-start mb-4">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <Icon className={`h-6 w-6 text-${typeInfo.color}-500`} />
                  <Badge variant="secondary">{typeInfo.label}</Badge>
                  {!insight.is_read && (
                    <Badge variant="default" className="bg-blue-500">New</Badge>
                  )}
                </div>
                <h2 className="text-2xl font-bold">{insight.title}</h2>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedInsight(null)}
              >
                ✕
              </Button>
            </div>

            <div className="space-y-4">
              <div>
                <h3 className="font-semibold mb-2">Description</h3>
                <p className="text-gray-700">{insight.description}</p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h4 className="text-sm font-semibold text-gray-500">Confidence Level</h4>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="flex-1 bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-blue-500 h-2 rounded-full"
                        style={{ width: `${insight.confidence * 100}%` }}
                      />
                    </div>
                    <span className={`font-semibold ${getConfidenceColor(insight.confidence)}`}>
                      {Math.round(insight.confidence * 100)}%
                    </span>
                  </div>
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-gray-500">Impact Score</h4>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="flex-1 bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-green-500 h-2 rounded-full"
                        style={{ width: `${insight.impact_score * 100}%` }}
                      />
                    </div>
                    <span className="font-semibold">
                      {Math.round(insight.impact_score * 100)}%
                    </span>
                  </div>
                </div>
              </div>

              {insight.recommendations && insight.recommendations.length > 0 && (
                <div>
                  <h3 className="font-semibold mb-2">Recommendations</h3>
                  <div className="space-y-2">
                    {insight.recommendations.map((rec, idx) => (
                      <div key={idx} className="flex items-start gap-2 p-3 bg-blue-50 rounded-lg">
                        <CheckCircle className="h-5 w-5 text-blue-500 mt-0.5 flex-shrink-0" />
                        <p className="text-sm">{rec}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {insight.supporting_patterns && insight.supporting_patterns.length > 0 && (
                <div>
                  <h3 className="font-semibold mb-2">Based on Patterns</h3>
                  <div className="flex flex-wrap gap-2">
                    {insight.supporting_patterns.map((patternId, idx) => (
                      <Badge key={idx} variant="outline">
                        Pattern #{idx + 1}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex gap-2 pt-4 border-t">
                {!insight.is_read && (
                  <Button
                    variant="outline"
                    onClick={() => markAsRead(insight.id)}
                  >
                    <Eye className="h-4 w-4 mr-2" />
                    Mark as Read
                  </Button>
                )}
                {!insight.action_taken && (
                  <Button
                    variant="default"
                    onClick={() => markActionTaken(insight.id)}
                  >
                    <ThumbsUp className="h-4 w-4 mr-2" />
                    Action Taken
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Behavioral Insights</h1>
        <p className="text-gray-600">
          Personalized insights and recommendations based on your patterns
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Insights</p>
                <p className="text-2xl font-bold">{stats.total}</p>
              </div>
              <Lightbulb className="h-8 w-8 text-yellow-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Unread</p>
                <p className="text-2xl font-bold">{stats.unread}</p>
              </div>
              <EyeOff className="h-8 w-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Actions Taken</p>
                <p className="text-2xl font-bold">{stats.actionTaken}</p>
              </div>
              <CheckCircle className="h-8 w-8 text-green-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs value={selectedType} onValueChange={setSelectedType} className="mb-6">
        <TabsList className="grid w-full grid-cols-6">
          <TabsTrigger value="all">All</TabsTrigger>
          {Object.entries(insightTypes).map(([key, info]) => (
            <TabsTrigger key={key} value={key}>
              {info.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      <div className="mb-4 flex gap-2">
        <Button
          variant={unreadOnly ? "default" : "outline"}
          onClick={() => setUnreadOnly(!unreadOnly)}
        >
          {unreadOnly ? 'Show All' : 'Show Unread Only'}
        </Button>
        <Button onClick={fetchInsights} variant="outline">
          Refresh
        </Button>
      </div>

      {loading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      ) : insights.length === 0 ? (
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            {unreadOnly 
              ? "No unread insights. Great job staying on top of things!"
              : "No insights available yet. Keep using the system to generate insights."}
          </AlertDescription>
        </Alert>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {insights.map((insight) => (
              <InsightCard key={insight.id} insight={insight} />
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

      {selectedInsight && <InsightDetail insight={selectedInsight} />}
    </div>
  );
};

export default InsightsPage;