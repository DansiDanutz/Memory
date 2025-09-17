import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Brain, 
  MessageCircle, 
  Mic, 
  Smartphone, 
  Shield, 
  Zap,
  ArrowRight,
  Check,
  Star
} from 'lucide-react';

// Components
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';

// Hooks
import { useTheme } from '../contexts/ThemeContext';

const WelcomePage = ({ onComplete }) => {
  const navigate = useNavigate();
  const { isDark } = useTheme();
  const [currentStep, setCurrentStep] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);

  const steps = [
    {
      id: 'welcome',
      title: 'Welcome to Memo',
      subtitle: 'Your Personal AI Brain',
      description: 'Transform how you capture, organize, and recall your memories with AI-powered intelligence.',
      icon: Brain,
      color: '#39FF14',
      features: [
        'AI-powered memory organization',
        'WhatsApp-like familiar interface',
        'Cross-platform synchronization',
        'Voice recording & transcription'
      ]
    },
    {
      id: 'interface',
      title: 'Familiar Interface',
      subtitle: 'Just like WhatsApp',
      description: 'Navigate effortlessly with an interface you already know and love.',
      icon: MessageCircle,
      color: '#00D9FF',
      features: [
        'Intuitive chat-based interaction',
        'Memory categories in sidebar',
        'Real-time message sync',
        'Professional dark theme'
      ]
    },
    {
      id: 'voice',
      title: 'Voice Integration',
      subtitle: 'Speak Your Thoughts',
      description: 'Record voice memos and let AI transcribe and organize them automatically.',
      icon: Mic,
      color: '#FF6B6B',
      features: [
        'High-quality voice recording',
        'Automatic transcription',
        'Voice command support',
        'Multi-language support'
      ]
    },
    {
      id: 'sync',
      title: 'Cross-Platform Sync',
      subtitle: 'Always Connected',
      description: 'Access your memories anywhere with seamless synchronization across all devices.',
      icon: Smartphone,
      color: '#4ECDC4',
      features: [
        'Real-time synchronization',
        'WhatsApp integration',
        'Multi-device support',
        'Offline mode available'
      ]
    },
    {
      id: 'security',
      title: 'Privacy & Security',
      subtitle: 'Your Data is Safe',
      description: 'Enterprise-grade security ensures your memories remain private and secure.',
      icon: Shield,
      color: '#45B7D1',
      features: [
        'End-to-end encryption',
        'Local data storage',
        'Privacy-first design',
        'GDPR compliant'
      ]
    },
    {
      id: 'ready',
      title: 'Ready to Begin?',
      subtitle: 'Start Your Memory Journey',
      description: 'Join thousands of users who have transformed their memory management.',
      icon: Zap,
      color: '#96CEB4',
      features: [
        'Get started in seconds',
        'No credit card required',
        'Free tier available',
        '24/7 support'
      ]
    }
  ];

  const currentStepData = steps[currentStep];

  useEffect(() => {
    // Auto-advance after 5 seconds on each step (except the last one)
    if (currentStep < steps.length - 1) {
      const timer = setTimeout(() => {
        nextStep();
      }, 8000);
      return () => clearTimeout(timer);
    }
  }, [currentStep]);

  const nextStep = () => {
    if (isAnimating) return;
    
    setIsAnimating(true);
    setTimeout(() => {
      setCurrentStep(prev => Math.min(prev + 1, steps.length - 1));
      setIsAnimating(false);
    }, 300);
  };

  const prevStep = () => {
    if (isAnimating) return;
    
    setIsAnimating(true);
    setTimeout(() => {
      setCurrentStep(prev => Math.max(prev - 1, 0));
      setIsAnimating(false);
    }, 300);
  };

  const handleGetStarted = () => {
    onComplete();
    navigate('/chat');
  };

  const skipOnboarding = () => {
    onComplete();
    navigate('/chat');
  };

  return (
    <div className={`min-h-screen bg-gradient-to-br from-background via-background to-muted ${isDark ? 'dark' : ''}`}>
      {/* Background Pattern */}
      <div className="absolute inset-0 opacity-5">
        <div className="absolute inset-0" style={{
          backgroundImage: `radial-gradient(circle at 25% 25%, ${currentStepData.color}40 0%, transparent 50%), 
                           radial-gradient(circle at 75% 75%, ${currentStepData.color}20 0%, transparent 50%)`
        }} />
      </div>

      <div className="relative z-10 min-h-screen flex flex-col">
        {/* Header */}
        <header className="p-6 flex justify-between items-center">
          <div className="flex items-center space-x-3">
            <div 
              className="w-10 h-10 rounded-full flex items-center justify-center"
              style={{ backgroundColor: currentStepData.color + '20', border: `2px solid ${currentStepData.color}` }}
            >
              <Brain className="w-5 h-5" style={{ color: currentStepData.color }} />
            </div>
            <div>
              <h1 className="text-xl font-bold text-foreground">Memo</h1>
              <p className="text-sm text-muted-foreground">Personal AI Brain</p>
            </div>
          </div>
          
          <Button 
            variant="ghost" 
            onClick={skipOnboarding}
            className="text-muted-foreground hover:text-foreground"
          >
            Skip
          </Button>
        </header>

        {/* Progress Bar */}
        <div className="px-6 mb-8">
          <div className="flex items-center space-x-2 mb-2">
            <span className="text-sm text-muted-foreground">
              Step {currentStep + 1} of {steps.length}
            </span>
            <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
              <motion.div
                className="h-full rounded-full"
                style={{ backgroundColor: currentStepData.color }}
                initial={{ width: 0 }}
                animate={{ width: `${((currentStep + 1) / steps.length) * 100}%` }}
                transition={{ duration: 0.5, ease: 'easeOut' }}
              />
            </div>
          </div>
        </div>

        {/* Main Content */}
        <main className="flex-1 px-6 pb-6">
          <div className="max-w-4xl mx-auto">
            <AnimatePresence mode="wait">
              <motion.div
                key={currentStep}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.5 }}
                className="text-center mb-12"
              >
                {/* Icon */}
                <motion.div
                  className="w-24 h-24 mx-auto mb-6 rounded-full flex items-center justify-center"
                  style={{ 
                    backgroundColor: currentStepData.color + '20',
                    border: `3px solid ${currentStepData.color}`
                  }}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <currentStepData.icon 
                    className="w-12 h-12" 
                    style={{ color: currentStepData.color }}
                  />
                </motion.div>

                {/* Title & Subtitle */}
                <h2 className="text-4xl md:text-5xl font-bold text-foreground mb-2">
                  {currentStepData.title}
                </h2>
                <p 
                  className="text-xl md:text-2xl font-medium mb-4"
                  style={{ color: currentStepData.color }}
                >
                  {currentStepData.subtitle}
                </p>
                <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                  {currentStepData.description}
                </p>
              </motion.div>
            </AnimatePresence>

            {/* Features Grid */}
            <motion.div
              key={`features-${currentStep}`}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-12"
            >
              {currentStepData.features.map((feature, index) => (
                <motion.div
                  key={feature}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, delay: 0.3 + index * 0.1 }}
                >
                  <Card className="p-4 border-border/50 hover:border-border transition-colors">
                    <div className="flex items-center space-x-3">
                      <div 
                        className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                        style={{ backgroundColor: currentStepData.color + '20' }}
                      >
                        <Check 
                          className="w-4 h-4" 
                          style={{ color: currentStepData.color }}
                        />
                      </div>
                      <span className="text-foreground font-medium">{feature}</span>
                    </div>
                  </Card>
                </motion.div>
              ))}
            </motion.div>

            {/* Testimonial (for last step) */}
            {currentStep === steps.length - 1 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.4 }}
                className="mb-12"
              >
                <Card className="p-6 bg-muted/50 border-border/50">
                  <div className="flex items-center space-x-1 mb-3">
                    {[...Array(5)].map((_, i) => (
                      <Star key={i} className="w-5 h-5 fill-yellow-400 text-yellow-400" />
                    ))}
                  </div>
                  <blockquote className="text-lg text-foreground mb-4">
                    "Memo has completely transformed how I manage my thoughts and ideas. 
                    The AI-powered organization is incredible, and the WhatsApp-like interface 
                    makes it so natural to use."
                  </blockquote>
                  <cite className="text-muted-foreground">
                    — Sarah Chen, Product Manager
                  </cite>
                </Card>
              </motion.div>
            )}
          </div>
        </main>

        {/* Navigation */}
        <footer className="p-6">
          <div className="max-w-4xl mx-auto flex justify-between items-center">
            <Button
              variant="ghost"
              onClick={prevStep}
              disabled={currentStep === 0 || isAnimating}
              className="flex items-center space-x-2"
            >
              <ArrowRight className="w-4 h-4 rotate-180" />
              <span>Previous</span>
            </Button>

            <div className="flex space-x-2">
              {steps.map((_, index) => (
                <button
                  key={index}
                  onClick={() => setCurrentStep(index)}
                  className={`w-3 h-3 rounded-full transition-all duration-300 ${
                    index === currentStep
                      ? 'scale-125'
                      : 'scale-100 opacity-50 hover:opacity-75'
                  }`}
                  style={{
                    backgroundColor: index === currentStep 
                      ? currentStepData.color 
                      : isDark ? '#6B7280' : '#9CA3AF'
                  }}
                />
              ))}
            </div>

            {currentStep === steps.length - 1 ? (
              <Button
                onClick={handleGetStarted}
                className="flex items-center space-x-2 px-6 py-3"
                style={{ 
                  backgroundColor: currentStepData.color,
                  color: isDark ? '#0D1117' : '#FFFFFF'
                }}
              >
                <span>Get Started</span>
                <ArrowRight className="w-4 h-4" />
              </Button>
            ) : (
              <Button
                variant="ghost"
                onClick={nextStep}
                disabled={isAnimating}
                className="flex items-center space-x-2"
              >
                <span>Next</span>
                <ArrowRight className="w-4 h-4" />
              </Button>
            )}
          </div>
        </footer>
      </div>
    </div>
  );
};

export default WelcomePage;

