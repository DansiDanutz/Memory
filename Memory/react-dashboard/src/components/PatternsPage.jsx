import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../config';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { TrendingUp, Activity, Users, MapPin, Heart, MessageSquare, Calendar, Home } from 'lucide-react';

const PatternsPage = ({ user }) => {
  const [patterns, setPatterns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedType, setSelectedType] = useState('all');
  const [minStrength, setMinStrength] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [selectedPattern, setSelectedPattern] = useState(null);

  const patternTypes = {
    temporal: { icon: Calendar, color: 'blue', label: 'Temporal' },
    behavioral: { icon: Activity, color: 'green', label: 'Behavioral' },
    social: { icon: Users, color: 'purple', label: 'Social' },
    location: { icon: MapPin, color: 'orange', label: 'Location' },
    emotional: { icon: Heart, color: 'red', label: 'Emotional' },
    activity: { icon: TrendingUp, color: 'indigo', label: 'Activity' },
    communication: { icon: MessageSquare, color: 'pink', label: 'Communication' },
    routine: { icon: Home, color: 'yellow', label: 'Routine' }
  };

  useEffect(() => {
    fetchPatterns();
  }, [selectedType, minStrength, page]);

  const fetchPatterns = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page,
        per_page: 12,
        ...(selectedType !== 'all' && { pattern_type: selectedType }),
        min_strength: minStrength
      });

      const response = await fetch(`${API_BASE_URL}/api/patterns?${params}`, {
        credentials: 'include'
      });

      const data = await response.json();
      if (data.success) {
        setPatterns(data.patterns);
        setTotalPages(data.pagination.total_pages);
      }
    } catch (error) {
      console.error('Error fetching patterns:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStrengthLabel = (strength) => {
    if (strength >= 0.85) return 'Very Strong';
    if (strength >= 0.7) return 'Strong';
    if (strength >= 0.5) return 'Moderate';
    return 'Weak';
  };

  const getStrengthColor = (strength) => {
    if (strength >= 0.85) return 'text-green-600';
    if (strength >= 0.7) return 'text-blue-600';
    if (strength >= 0.5) return 'text-yellow-600';
    return 'text-gray-600';
  };

  const PatternCard = ({ pattern }) => {
    const typeInfo = patternTypes[pattern.type] || patternTypes.behavioral;
    const Icon = typeInfo.icon;

    return (
      <Card 
        className="hover:shadow-lg transition-shadow cursor-pointer"
        onClick={() => setSelectedPattern(pattern)}
      >
        <CardHeader>
          <div className="flex justify-between items-start">
            <div className="flex items-center gap-2">
              <Icon className={`h-5 w-5 text-${typeInfo.color}-500`} />
              <Badge variant="secondary">{typeInfo.label}</Badge>
            </div>
            <span className={`text-sm font-semibold ${getStrengthColor(pattern.strength)}`}>
              {getStrengthLabel(pattern.strength)}
            </span>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-700 mb-3">{pattern.description}</p>
          
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span>Pattern Strength</span>
              <span>{Math.round(pattern.strength * 100)}%</span>
            </div>
            <Progress value={pattern.strength * 100} className="h-2" />
            
            <div className="flex justify-between text-xs">
              <span>Confidence</span>
              <span>{Math.round(pattern.confidence * 100)}%</span>
            </div>
            <Progress value={pattern.confidence * 100} className="h-2" />
          </div>

          {pattern.frequency && (
            <div className="mt-3 text-xs text-gray-500">
              Frequency: {JSON.stringify(pattern.frequency)}
            </div>
          )}

          {pattern.triggers && pattern.triggers.length > 0 && (
            <div className="mt-2">
              <span className="text-xs text-gray-500">Triggers:</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {pattern.triggers.slice(0, 3).map((trigger, idx) => (
                  <Badge key={idx} variant="outline" className="text-xs">
                    {trigger}
                  </Badge>
                ))}
                {pattern.triggers.length > 3 && (
                  <Badge variant="outline" className="text-xs">
                    +{pattern.triggers.length - 3} more
                  </Badge>
                )}
              </div>
            </div>
          )}

          {pattern.participants && pattern.participants.length > 0 && (
            <div className="mt-2 text-xs text-gray-500">
              Participants: {pattern.participants.join(', ')}
            </div>
          )}

          <div className="mt-3 flex justify-between text-xs text-gray-400">
            <span>First detected: {new Date(pattern.first_detected).toLocaleDateString()}</span>
            <span>{pattern.supporting_memories.length} memories</span>
          </div>
        </CardContent>
      </Card>
    );
  };

  const PatternDetail = ({ pattern }) => {
    const typeInfo = patternTypes[pattern.type] || patternTypes.behavioral;
    const Icon = typeInfo.icon;

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
        <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
          <div className="p-6">
            <div className="flex justify-between items-start mb-4">
              <div className="flex items-center gap-2">
                <Icon className={`h-6 w-6 text-${typeInfo.color}-500`} />
                <h2 className="text-2xl font-bold">{typeInfo.label} Pattern</h2>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedPattern(null)}
              >
                ✕
              </Button>
            </div>

            <div className="space-y-4">
              <div>
                <h3 className="font-semibold mb-2">Description</h3>
                <p className="text-gray-700">{pattern.description}</p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h4 className="text-sm font-semibold text-gray-500">Pattern Strength</h4>
                  <div className="flex items-center gap-2">
                    <Progress value={pattern.strength * 100} className="flex-1" />
                    <span className={`font-semibold ${getStrengthColor(pattern.strength)}`}>
                      {Math.round(pattern.strength * 100)}%
                    </span>
                  </div>
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-gray-500">Confidence</h4>
                  <div className="flex items-center gap-2">
                    <Progress value={pattern.confidence * 100} className="flex-1" />
                    <span className="font-semibold">
                      {Math.round(pattern.confidence * 100)}%
                    </span>
                  </div>
                </div>
              </div>

              {pattern.triggers && pattern.triggers.length > 0 && (
                <div>
                  <h3 className="font-semibold mb-2">Triggers</h3>
                  <div className="flex flex-wrap gap-2">
                    {pattern.triggers.map((trigger, idx) => (
                      <Badge key={idx} variant="secondary">
                        {trigger}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {pattern.time_windows && pattern.time_windows.length > 0 && (
                <div>
                  <h3 className="font-semibold mb-2">Time Windows</h3>
                  <div className="space-y-1">
                    {pattern.time_windows.map((window, idx) => (
                      <div key={idx} className="text-sm text-gray-600">
                        {JSON.stringify(window)}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {pattern.locations && pattern.locations.length > 0 && (
                <div>
                  <h3 className="font-semibold mb-2">Locations</h3>
                  <div className="flex flex-wrap gap-2">
                    {pattern.locations.map((location, idx) => (
                      <Badge key={idx} variant="outline">
                        {location}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {pattern.participants && pattern.participants.length > 0 && (
                <div>
                  <h3 className="font-semibold mb-2">Participants</h3>
                  <div className="flex flex-wrap gap-2">
                    {pattern.participants.map((participant, idx) => (
                      <Badge key={idx}>
                        {participant}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <h3 className="font-semibold mb-2">Statistics</h3>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-gray-500">Supporting Memories:</span>
                    <span className="ml-2 font-semibold">{pattern.supporting_memories.length}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Prediction Accuracy:</span>
                    <span className="ml-2 font-semibold">
                      {Math.round(pattern.prediction_accuracy * 100)}%
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500">First Detected:</span>
                    <span className="ml-2">{new Date(pattern.first_detected).toLocaleDateString()}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Last Updated:</span>
                    <span className="ml-2">{new Date(pattern.last_updated).toLocaleDateString()}</span>
                  </div>
                </div>
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
        <h1 className="text-3xl font-bold mb-2">Behavioral Patterns</h1>
        <p className="text-gray-600">
          Discover patterns in your behavior, habits, and routines
        </p>
      </div>

      <div className="mb-6 flex gap-4 flex-wrap">
        <Select value={selectedType} onValueChange={setSelectedType}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Pattern Type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            {Object.entries(patternTypes).map(([key, info]) => (
              <SelectItem key={key} value={key}>
                {info.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={minStrength.toString()} onValueChange={(v) => setMinStrength(parseFloat(v))}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Minimum Strength" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="0">All Patterns</SelectItem>
            <SelectItem value="0.3">Weak+</SelectItem>
            <SelectItem value="0.5">Moderate+</SelectItem>
            <SelectItem value="0.7">Strong+</SelectItem>
            <SelectItem value="0.85">Very Strong</SelectItem>
          </SelectContent>
        </Select>

        <Button onClick={fetchPatterns} variant="outline">
          Refresh
        </Button>
      </div>

      {loading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      ) : patterns.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12">
            <p className="text-gray-500">No patterns found with the selected filters</p>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {patterns.map((pattern) => (
              <PatternCard key={pattern.id} pattern={pattern} />
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

      {selectedPattern && <PatternDetail pattern={selectedPattern} />}
    </div>
  );
};

export default PatternsPage;