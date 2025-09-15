import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../config';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { Alert, AlertDescription } from './ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { 
  Play, Pause, CheckCircle, XCircle, Clock, RefreshCw,
  Database, TrendingUp, Lightbulb, FileText, Archive,
  ChevronRight, AlertCircle, Info
} from 'lucide-react';

const JobStatus = ({ user }) => {
  const [activeJobs, setActiveJobs] = useState([]);
  const [jobHistory, setJobHistory] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const jobTypes = {
    harvest: { 
      icon: Database, 
      color: 'blue', 
      label: 'Memory Harvest',
      description: 'Collecting memories from various sources'
    },
    pattern_analysis: { 
      icon: TrendingUp, 
      color: 'green', 
      label: 'Pattern Analysis',
      description: 'Analyzing behavioral patterns'
    },
    insight_generation: { 
      icon: Lightbulb, 
      color: 'yellow', 
      label: 'Insight Generation',
      description: 'Generating personalized insights'
    },
    daily_digest: { 
      icon: FileText, 
      color: 'purple', 
      label: 'Daily Digest',
      description: 'Preparing your daily memory digest'
    },
    backup: { 
      icon: Archive, 
      color: 'gray', 
      label: 'Backup',
      description: 'Backing up your data'
    }
  };

  const jobStatuses = {
    pending: { color: 'gray', label: 'Pending', icon: Clock },
    running: { color: 'blue', label: 'Running', icon: RefreshCw },
    completed: { color: 'green', label: 'Completed', icon: CheckCircle },
    failed: { color: 'red', label: 'Failed', icon: XCircle },
    cancelled: { color: 'orange', label: 'Cancelled', icon: XCircle }
  };

  useEffect(() => {
    fetchJobs();
    const interval = autoRefresh ? setInterval(fetchJobs, 5000) : null;
    return () => interval && clearInterval(interval);
  }, [autoRefresh]);

  const fetchJobs = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/jobs`, {
        credentials: 'include'
      });

      const data = await response.json();
      if (data.success) {
        // Separate active and completed jobs
        const active = data.jobs.filter(j => 
          j.status === 'pending' || j.status === 'running'
        );
        const history = data.jobs.filter(j => 
          j.status === 'completed' || j.status === 'failed' || j.status === 'cancelled'
        );
        
        setActiveJobs(active);
        setJobHistory(history);
      }
    } catch (error) {
      console.error('Error fetching jobs:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchJobDetails = async (jobId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/jobs/${jobId}`, {
        credentials: 'include'
      });

      const data = await response.json();
      if (data.success) {
        setSelectedJob(data.job);
      }
    } catch (error) {
      console.error('Error fetching job details:', error);
    }
  };

  const enqueueHarvestJob = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/harvest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          sources: ['chat_message', 'email', 'calendar_event'],
          time_range: { days: 1 }
        })
      });

      const data = await response.json();
      if (data.success) {
        fetchJobs(); // Refresh job list
      }
    } catch (error) {
      console.error('Error enqueueing harvest job:', error);
    }
  };

  const formatDuration = (start, end) => {
    if (!start || !end) return 'N/A';
    const duration = new Date(end) - new Date(start);
    const seconds = Math.floor(duration / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    
    if (hours > 0) return `${hours}h ${minutes % 60}m`;
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
    return `${seconds}s`;
  };

  const JobCard = ({ job, detailed = false }) => {
    const typeInfo = jobTypes[job.type] || jobTypes.harvest;
    const statusInfo = jobStatuses[job.status] || jobStatuses.pending;
    const Icon = typeInfo.icon;
    const StatusIcon = statusInfo.icon;

    return (
      <Card 
        className={`${!detailed ? 'hover:shadow-lg transition-shadow cursor-pointer' : ''}`}
        onClick={!detailed ? () => fetchJobDetails(job.id) : undefined}
      >
        <CardHeader>
          <div className="flex justify-between items-start">
            <div className="flex items-center gap-2">
              <Icon className={`h-5 w-5 text-${typeInfo.color}-500`} />
              <div>
                <CardTitle className="text-lg">{typeInfo.label}</CardTitle>
                <CardDescription className="text-xs">
                  {typeInfo.description}
                </CardDescription>
              </div>
            </div>
            <Badge 
              variant={job.status === 'running' ? 'default' : 'outline'}
              className={`text-${statusInfo.color}-600`}
            >
              <StatusIcon className="h-3 w-3 mr-1" />
              {statusInfo.label}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          {job.status === 'running' && (
            <div className="mb-3">
              <div className="flex justify-between text-sm mb-1">
                <span>Progress</span>
                <span>{job.progress}%</span>
              </div>
              <Progress value={job.progress} className="h-2" />
            </div>
          )}

          {detailed && job.result && (
            <div className="mb-3 p-3 bg-gray-50 rounded">
              <h4 className="text-sm font-semibold mb-2">Result</h4>
              <pre className="text-xs overflow-x-auto">
                {JSON.stringify(job.result, null, 2)}
              </pre>
            </div>
          )}

          {detailed && job.error && (
            <Alert className="mb-3">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {job.error}
              </AlertDescription>
            </Alert>
          )}

          <div className="text-xs text-gray-500 space-y-1">
            <div className="flex justify-between">
              <span>Job ID:</span>
              <span className="font-mono">{job.id.slice(0, 8)}...</span>
            </div>
            {job.created_at && (
              <div className="flex justify-between">
                <span>Created:</span>
                <span>{new Date(job.created_at).toLocaleString()}</span>
              </div>
            )}
            {job.started_at && (
              <div className="flex justify-between">
                <span>Started:</span>
                <span>{new Date(job.started_at).toLocaleString()}</span>
              </div>
            )}
            {job.completed_at && (
              <div className="flex justify-between">
                <span>Completed:</span>
                <span>{new Date(job.completed_at).toLocaleString()}</span>
              </div>
            )}
            {job.started_at && job.completed_at && (
              <div className="flex justify-between">
                <span>Duration:</span>
                <span>{formatDuration(job.started_at, job.completed_at)}</span>
              </div>
            )}
          </div>

          {!detailed && (
            <div className="mt-3 flex items-center text-xs text-blue-500">
              View details
              <ChevronRight className="h-3 w-3 ml-1" />
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  const JobDetail = ({ job }) => {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
        <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
          <div className="p-6">
            <div className="flex justify-between items-start mb-4">
              <h2 className="text-2xl font-bold">Job Details</h2>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedJob(null)}
              >
                ✕
              </Button>
            </div>
            
            <JobCard job={job} detailed={true} />
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Background Jobs</h1>
        <p className="text-gray-600">
          Monitor and manage background processing tasks
        </p>
      </div>

      <div className="mb-6 flex gap-2">
        <Button
          variant="default"
          onClick={enqueueHarvestJob}
        >
          <Play className="h-4 w-4 mr-2" />
          Run Harvest Job
        </Button>
        <Button
          variant={autoRefresh ? "default" : "outline"}
          onClick={() => setAutoRefresh(!autoRefresh)}
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${autoRefresh ? 'animate-spin' : ''}`} />
          {autoRefresh ? 'Auto-Refresh On' : 'Auto-Refresh Off'}
        </Button>
        <Button
          variant="outline"
          onClick={fetchJobs}
        >
          Refresh Now
        </Button>
      </div>

      <Tabs defaultValue="active" className="mb-6">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="active">
            Active Jobs ({activeJobs.length})
          </TabsTrigger>
          <TabsTrigger value="history">
            Job History ({jobHistory.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="active">
          {loading ? (
            <div className="flex justify-center items-center h-64">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
            </div>
          ) : activeJobs.length === 0 ? (
            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>
                No active jobs running. Background tasks are scheduled to run automatically at specific times.
              </AlertDescription>
            </Alert>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {activeJobs.map((job) => (
                <JobCard key={job.id} job={job} />
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="history">
          {loading ? (
            <div className="flex justify-center items-center h-64">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
            </div>
          ) : jobHistory.length === 0 ? (
            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>
                No job history available yet.
              </AlertDescription>
            </Alert>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {jobHistory.map((job) => (
                <JobCard key={job.id} job={job} />
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Job Schedule Information */}
      <Card>
        <CardHeader>
          <CardTitle>Scheduled Jobs</CardTitle>
          <CardDescription>
            Automatic jobs that run on a schedule
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
              <div className="flex items-center gap-2">
                <Database className="h-4 w-4 text-blue-500" />
                <div>
                  <p className="font-semibold text-sm">Daily Memory Harvest</p>
                  <p className="text-xs text-gray-500">Collects memories from all sources</p>
                </div>
              </div>
              <Badge variant="outline">2:00 AM UTC</Badge>
            </div>
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
              <div className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-green-500" />
                <div>
                  <p className="font-semibold text-sm">Pattern Analysis</p>
                  <p className="text-xs text-gray-500">Analyzes behavioral patterns</p>
                </div>
              </div>
              <Badge variant="outline">3:00 AM UTC</Badge>
            </div>
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
              <div className="flex items-center gap-2">
                <Lightbulb className="h-4 w-4 text-yellow-500" />
                <div>
                  <p className="font-semibold text-sm">Insight Generation</p>
                  <p className="text-xs text-gray-500">Creates personalized insights</p>
                </div>
              </div>
              <Badge variant="outline">4:00 AM UTC</Badge>
            </div>
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-purple-500" />
                <div>
                  <p className="font-semibold text-sm">Daily Digest</p>
                  <p className="text-xs text-gray-500">Prepares your daily summary</p>
                </div>
              </div>
              <Badge variant="outline">6:00 AM UTC</Badge>
            </div>
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
              <div className="flex items-center gap-2">
                <Archive className="h-4 w-4 text-gray-500" />
                <div>
                  <p className="font-semibold text-sm">Daily Backup</p>
                  <p className="text-xs text-gray-500">Backs up all your data</p>
                </div>
              </div>
              <Badge variant="outline">1:00 AM UTC</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {selectedJob && <JobDetail job={selectedJob} />}
    </div>
  );
};

export default JobStatus;