import React, { useState, useContext, useEffect } from 'react';
import {
  Search, MoreVertical, Phone, Video, Settings, Moon, Sun,
  MessageCircle, Brain, Trophy, Star, Gift, Crown, Sparkles,
  Bell, Lock, Users, Home, Plus, User, ChevronRight,
  Zap, Target, Flame, ArrowUp, TrendingUp
} from 'lucide-react';
import { ThemeContext } from '../contexts/ThemeContext';
import { Button } from './ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Avatar, AvatarFallback, AvatarImage } from './ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from './ui/dialog';

const ModernMemoryApp = () => {
  const { theme, toggleTheme } = useContext(ThemeContext);
  const [selectedTab, setSelectedTab] = useState('home');

  // Sample data for memory slots
  const [memorySlots] = useState([
    { id: 1, name: 'Sarah Chen', initials: 'SC', lastActive: '2 min ago', score: 850, streak: 12, avatar: null, memories: 42 },
    { id: 2, name: 'Alex Kumar', initials: 'AK', lastActive: '15 min ago', score: 720, streak: 8, avatar: null, memories: 38 },
    { id: 3, name: 'Emily Davis', initials: 'ED', lastActive: '1 hour ago', score: 690, streak: 5, avatar: null, memories: 29 },
    { id: 4, name: 'James Wilson', initials: 'JW', lastActive: '3 hours ago', score: 580, streak: 3, avatar: null, memories: 24 },
    { id: 5, name: 'Empty Slot', initials: '+', isEmpty: true },
    { id: 6, name: 'Premium Slot', initials: '👑', isPremium: true, locked: true }
  ]);

  const [stats] = useState({
    totalMemories: 133,
    weeklyProgress: 68,
    currentStreak: 12,
    totalPoints: 2840
  });

  const achievements = [
    { id: 1, title: 'Memory Master', description: 'Completed 100 memories', icon: Brain, progress: 100, total: 100, unlocked: true, color: 'text-purple-500' },
    { id: 2, title: 'Streak Champion', description: '7 day streak', icon: Flame, progress: 7, total: 7, unlocked: true, color: 'text-orange-500' },
    { id: 3, title: 'Social Butterfly', description: 'Connect with 10 friends', icon: Users, progress: 4, total: 10, unlocked: false, color: 'text-blue-500' },
    { id: 4, title: 'Rising Star', description: 'Earn 5000 points', icon: Star, progress: 2840, total: 5000, unlocked: false, color: 'text-yellow-500' }
  ];

  return (
    <div className={`min-h-screen transition-colors duration-300 ${
      theme === 'dark' ? 'bg-gray-950 text-white' : 'bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50'
    }`}>
      {/* Modern Header */}
      <header className={`sticky top-0 z-50 backdrop-blur-xl ${
        theme === 'dark' ? 'bg-gray-900/80 border-gray-800' : 'bg-white/80 border-gray-200'
      } border-b`}>
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="relative">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center">
                  <Brain className="w-6 h-6 text-white" />
                </div>
                <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-white"></div>
              </div>
              <div>
                <h1 className="text-xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
                  Memory Companion
                </h1>
                <p className={`text-xs ${theme === 'dark' ? 'text-gray-400' : 'text-gray-600'}`}>
                  {stats.totalMemories} memories saved
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button variant="ghost" size="icon" className="relative">
                <Bell className="w-5 h-5" />
                <span className="absolute top-0 right-0 w-2 h-2 bg-red-500 rounded-full"></span>
              </Button>

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon">
                    <Avatar className="w-8 h-8">
                      <AvatarImage src="" />
                      <AvatarFallback>U</AvatarFallback>
                    </Avatar>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent className="w-56">
                  <DropdownMenuLabel>My Account</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => {}}>
                    <User className="mr-2 h-4 w-4" />
                    Profile
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => {}}>
                    <Settings className="mr-2 h-4 w-4" />
                    Settings
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={toggleTheme}>
                    {theme === 'dark' ? <Sun className="mr-2 h-4 w-4" /> : <Moon className="mr-2 h-4 w-4" />}
                    {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </div>
      </header>

      {/* Stats Overview */}
      <div className="container mx-auto px-4 py-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <Card className={`${theme === 'dark' ? 'bg-gray-900 border-gray-800' : 'bg-white'} hover:shadow-lg transition-all`}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className={`text-sm ${theme === 'dark' ? 'text-gray-400' : 'text-gray-600'}`}>Total Points</p>
                  <p className="text-2xl font-bold">{stats.totalPoints}</p>
                </div>
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center">
                  <Trophy className="w-5 h-5 text-white" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className={`${theme === 'dark' ? 'bg-gray-900 border-gray-800' : 'bg-white'} hover:shadow-lg transition-all`}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className={`text-sm ${theme === 'dark' ? 'text-gray-400' : 'text-gray-600'}`}>Current Streak</p>
                  <p className="text-2xl font-bold">{stats.currentStreak} days</p>
                </div>
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center">
                  <Flame className="w-5 h-5 text-white" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className={`${theme === 'dark' ? 'bg-gray-900 border-gray-800' : 'bg-white'} hover:shadow-lg transition-all`}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className={`text-sm ${theme === 'dark' ? 'text-gray-400' : 'text-gray-600'}`}>Weekly Progress</p>
                  <p className="text-2xl font-bold">{stats.weeklyProgress}%</p>
                </div>
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center">
                  <TrendingUp className="w-5 h-5 text-white" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className={`${theme === 'dark' ? 'bg-gray-900 border-gray-800' : 'bg-white'} hover:shadow-lg transition-all`}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className={`text-sm ${theme === 'dark' ? 'text-gray-400' : 'text-gray-600'}`}>Memories</p>
                  <p className="text-2xl font-bold">{stats.totalMemories}</p>
                </div>
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
                  <Brain className="w-5 h-5 text-white" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main Content Tabs */}
        <Tabs value={selectedTab} onValueChange={setSelectedTab} className="w-full">
          <TabsList className={`grid w-full grid-cols-3 mb-6 ${theme === 'dark' ? 'bg-gray-900' : 'bg-white'}`}>
            <TabsTrigger value="home" className="flex items-center gap-2">
              <Home className="w-4 h-4" />
              Contacts
            </TabsTrigger>
            <TabsTrigger value="memories" className="flex items-center gap-2">
              <Brain className="w-4 h-4" />
              Memories
            </TabsTrigger>
            <TabsTrigger value="achievements" className="flex items-center gap-2">
              <Trophy className="w-4 h-4" />
              Achievements
            </TabsTrigger>
          </TabsList>

          {/* Contacts Tab */}
          <TabsContent value="home" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {memorySlots.map((slot) => (
                <Card
                  key={slot.id}
                  className={`${theme === 'dark' ? 'bg-gray-900 border-gray-800' : 'bg-white'}
                    ${slot.isEmpty || slot.locked ? 'opacity-60' : 'hover:shadow-xl cursor-pointer'}
                    transition-all transform hover:scale-105`}
                >
                  <CardContent className="p-6">
                    {slot.isEmpty ? (
                      <div className="flex flex-col items-center justify-center py-8">
                        <div className="w-16 h-16 rounded-full bg-gray-200 dark:bg-gray-800 flex items-center justify-center mb-4">
                          <Plus className="w-8 h-8 text-gray-400" />
                        </div>
                        <p className="text-gray-500 font-medium">Add Contact</p>
                        <p className="text-sm text-gray-400 mt-1">Connect a new friend</p>
                      </div>
                    ) : slot.locked ? (
                      <div className="flex flex-col items-center justify-center py-8">
                        <div className="w-16 h-16 rounded-full bg-gradient-to-br from-yellow-400 to-yellow-600 flex items-center justify-center mb-4">
                          <Lock className="w-8 h-8 text-white" />
                        </div>
                        <p className="font-bold text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 to-yellow-600">
                          Premium Slot
                        </p>
                        <p className="text-sm text-gray-400 mt-1">Upgrade to unlock</p>
                        <Button size="sm" className="mt-3 bg-gradient-to-r from-yellow-400 to-yellow-600 hover:from-yellow-500 hover:to-yellow-700">
                          <Crown className="w-4 h-4 mr-1" />
                          Upgrade
                        </Button>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <Avatar className="w-12 h-12">
                              <AvatarImage src={slot.avatar} />
                              <AvatarFallback className="bg-gradient-to-br from-purple-500 to-blue-600 text-white">
                                {slot.initials}
                              </AvatarFallback>
                            </Avatar>
                            <div>
                              <p className="font-semibold">{slot.name}</p>
                              <p className={`text-xs ${theme === 'dark' ? 'text-gray-400' : 'text-gray-500'}`}>
                                {slot.lastActive}
                              </p>
                            </div>
                          </div>
                          <Badge variant="outline" className="text-xs">
                            <Flame className="w-3 h-3 mr-1 text-orange-500" />
                            {slot.streak}
                          </Badge>
                        </div>

                        <div className="flex items-center justify-between pt-3 border-t dark:border-gray-800">
                          <div className="flex items-center gap-1">
                            <Brain className="w-4 h-4 text-purple-500" />
                            <span className="text-sm font-medium">{slot.memories}</span>
                            <span className="text-xs text-gray-500">memories</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <Trophy className="w-4 h-4 text-yellow-500" />
                            <span className="text-sm font-medium">{slot.score}</span>
                            <span className="text-xs text-gray-500">pts</span>
                          </div>
                        </div>

                        <Button className="w-full" size="sm" variant={theme === 'dark' ? 'secondary' : 'outline'}>
                          <MessageCircle className="w-4 h-4 mr-2" />
                          Start Session
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          {/* Memories Tab */}
          <TabsContent value="memories" className="space-y-4">
            <Card className={theme === 'dark' ? 'bg-gray-900 border-gray-800' : 'bg-white'}>
              <CardHeader>
                <CardTitle>Recent Memories</CardTitle>
                <CardDescription>Your latest memory training sessions</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className={`p-4 rounded-lg ${theme === 'dark' ? 'bg-gray-800' : 'bg-gray-50'}`}>
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-3">
                          <Avatar className="w-8 h-8">
                            <AvatarFallback>SC</AvatarFallback>
                          </Avatar>
                          <div>
                            <p className="font-medium">Sarah Chen</p>
                            <p className="text-xs text-gray-500">Completed 5 memories</p>
                          </div>
                        </div>
                        <Badge className="bg-green-100 text-green-800">+50 pts</Badge>
                      </div>
                      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                        <div className="bg-gradient-to-r from-purple-500 to-blue-600 h-2 rounded-full" style={{width: '75%'}}></div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Achievements Tab */}
          <TabsContent value="achievements" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {achievements.map((achievement) => {
                const Icon = achievement.icon;
                return (
                  <Card
                    key={achievement.id}
                    className={`${theme === 'dark' ? 'bg-gray-900 border-gray-800' : 'bg-white'}
                      ${!achievement.unlocked && 'opacity-60'}`}
                  >
                    <CardContent className="p-6">
                      <div className="flex items-start gap-4">
                        <div className={`w-12 h-12 rounded-xl ${
                          achievement.unlocked
                            ? 'bg-gradient-to-br from-purple-500 to-blue-600'
                            : theme === 'dark' ? 'bg-gray-800' : 'bg-gray-200'
                        } flex items-center justify-center`}>
                          <Icon className={`w-6 h-6 ${
                            achievement.unlocked ? 'text-white' : 'text-gray-400'
                          }`} />
                        </div>
                        <div className="flex-1">
                          <h3 className="font-semibold flex items-center gap-2">
                            {achievement.title}
                            {achievement.unlocked && <Sparkles className="w-4 h-4 text-yellow-500" />}
                          </h3>
                          <p className="text-sm text-gray-500 mt-1">{achievement.description}</p>
                          <div className="mt-3">
                            <div className="flex items-center justify-between text-xs mb-1">
                              <span>Progress</span>
                              <span>{achievement.progress}/{achievement.total}</span>
                            </div>
                            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                              <div
                                className="bg-gradient-to-r from-purple-500 to-blue-600 h-2 rounded-full transition-all"
                                style={{width: `${(achievement.progress / achievement.total) * 100}%`}}
                              ></div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default ModernMemoryApp;