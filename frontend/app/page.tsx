"use client"

import Link from 'next/link'
import { useEffect, useRef, useState } from 'react'
import { 
  Calendar, 
  Sparkles, 
  Zap, 
  Target, 
  TrendingUp, 
  Brain,
  ArrowRight,
  CheckCircle2,
  Clock,
  BarChart3,
  Users,
  Rocket,
  Linkedin,
  Briefcase,
  GraduationCap,
  Home as HomeIcon,
  UserCog
} from 'lucide-react'

export default function Home() {
  const [visibleSections, setVisibleSections] = useState<Set<string>>(new Set())
  const sectionRefs = useRef<{ [key: string]: HTMLDivElement | null }>({})

  useEffect(() => {
    const observerOptions = {
      root: null,
      rootMargin: '-100px 0px',
      threshold: 0.1
    }

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const sectionId = entry.target.getAttribute('data-section-id')
          if (sectionId) {
            setVisibleSections((prev) => new Set(prev).add(sectionId))
          }
        }
      })
    }, observerOptions)

    Object.values(sectionRefs.current).forEach((ref) => {
      if (ref) observer.observe(ref)
    })

    return () => {
      Object.values(sectionRefs.current).forEach((ref) => {
        if (ref) observer.unobserve(ref)
      })
    }
  }, [])

  const setSectionRef = (id: string) => (el: HTMLDivElement | null) => {
    sectionRefs.current[id] = el
  }

  return (
    <div className="min-h-screen overflow-x-hidden">
      {/* Hero Section */}
      <section 
        className="relative min-h-screen flex items-center justify-center overflow-hidden"
        data-section-id="hero"
        ref={setSectionRef('hero')}
      >
        {/* Animated gradient background */}
        <div className="absolute inset-0 bg-gradient-to-br from-purple-600 via-pink-500 to-blue-500 animate-gradient opacity-90"></div>
        
        {/* Floating geometric shapes */}
        <div className="absolute top-20 left-10 w-20 h-20 bg-white/10 rounded-full blur-xl animate-float"></div>
        <div className="absolute top-40 right-20 w-32 h-32 bg-pink-400/20 rounded-full blur-2xl animate-float-reverse"></div>
        <div className="absolute bottom-20 left-1/4 w-24 h-24 bg-blue-400/20 rounded-full blur-xl animate-float"></div>
        <div className="absolute bottom-40 right-1/3 w-28 h-28 bg-purple-400/20 rounded-full blur-2xl animate-float-reverse"></div>

        <div className="relative z-10 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className={`space-y-6 sm:space-y-8 ${visibleSections.has('hero') ? 'animate-fade-in-up' : 'opacity-0'}`}>
            <h1 className="text-5xl sm:text-6xl md:text-7xl lg:text-8xl xl:text-9xl 2xl:text-[12rem] font-bold leading-none tracking-tight relative">
              <span className="hero-gradient-text inline-block relative z-10" data-text="LifeFlow">LifeFlow</span>
            </h1>
            <p className="text-lg sm:text-xl md:text-2xl lg:text-3xl text-white/90 font-medium max-w-3xl mx-auto leading-relaxed px-2">
              Transform your to-do list into a <span className="font-bold text-white">done list</span> with AI-powered task management
            </p>
            <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 justify-center items-center pt-4 px-2">
              <Link
                href="/auth/register"
                className="group relative w-full sm:w-auto px-6 sm:px-8 py-3 sm:py-4 bg-white text-purple-600 font-bold text-base sm:text-lg rounded-full overflow-hidden transition-all duration-300 hover:scale-110 focus:outline-none focus:ring-4 focus:ring-white/50"
                aria-label="Get started with LifeFlow"
              >
                <span className="relative z-10 flex items-center justify-center gap-2 opacity-100 group-hover:opacity-0 transition-opacity duration-300">
                  Get Started Free
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </span>
                <div className="absolute inset-0 bg-gradient-to-r from-purple-500 to-pink-500 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                <span className="absolute inset-0 flex items-center justify-center gap-2 text-white opacity-0 group-hover:opacity-100 transition-opacity duration-300 z-10">
                  Get Started Free
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </span>
              </Link>
              <Link
                href="/auth/login"
                className="w-full sm:w-auto px-6 sm:px-8 py-3 sm:py-4 border-2 border-white/30 text-white font-bold text-base sm:text-lg rounded-full backdrop-blur-sm transition-all duration-300 hover:border-white hover:bg-white/10 hover:scale-110 focus:outline-none focus:ring-4 focus:ring-white/50"
                aria-label="Sign in to LifeFlow"
              >
                Sign In
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section 
        className="relative py-24 sm:py-32 bg-gradient-to-b from-gray-50 to-white dark:from-gray-900 dark:to-gray-800"
        data-section-id="features"
        ref={setSectionRef('features')}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className={`text-center mb-12 sm:mb-16 ${visibleSections.has('features') ? 'animate-fade-in-up' : 'opacity-0'}`}>
            <h2 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold mb-3 sm:mb-4 px-4">
              <span className="gradient-text">Powerful Features</span>
            </h2>
            <p className="text-lg sm:text-xl text-gray-600 dark:text-gray-400 max-w-2xl mx-auto px-4">
              Everything you need to master your productivity
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {[
              {
                icon: Calendar,
                title: 'Smart Calendar Sync',
                description: 'Automatically sync with Google Calendar and extract tasks from your events',
                delay: '0'
              },
              {
                icon: Sparkles,
                title: 'AI-Powered Extraction',
                description: 'Intelligent task identification using advanced NLP to understand your needs',
                delay: '100'
              },
              {
                icon: Zap,
                title: 'Energy-Aware Planning',
                description: 'Create personalized daily plans that match your energy levels',
                delay: '200'
              },
              {
                icon: Target,
                title: 'Priority Management',
                description: 'Mark tasks as critical or urgent to focus on what matters most',
                delay: '300'
              },
              {
                icon: Brain,
                title: 'Adaptive Learning',
                description: 'The system learns from your feedback to improve over time',
                delay: '400'
              },
              {
                icon: BarChart3,
                title: 'Progress Tracking',
                description: 'Monitor your task completion and productivity metrics',
                delay: '500'
              }
            ].map((feature, index) => {
              const Icon = feature.icon
              const isVisible = visibleSections.has('features')
              return (
                <div
                  key={index}
                  className={`group relative p-8 bg-white dark:bg-gray-800 rounded-2xl transition-all duration-300 hover:scale-105 border border-gray-100 dark:border-gray-700 ${
                    isVisible ? 'animate-scale-in' : 'opacity-0'
                  }`}
                  style={{ animationDelay: `${feature.delay}ms` }}
                >
                  <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-pink-500/10 dark:from-purple-500/20 dark:to-pink-500/20 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                  <div className="relative z-10">
                    <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                      <Icon className="w-8 h-8 text-white" />
                    </div>
                    <h3 className="text-2xl font-bold mb-3 text-gray-900 dark:text-gray-100 group-hover:text-transparent group-hover:bg-clip-text group-hover:bg-gradient-to-r group-hover:from-purple-600 group-hover:to-pink-600 transition-all duration-300">
                      {feature.title}
                    </h3>
                    <p className="text-gray-600 dark:text-gray-400 leading-relaxed">
                      {feature.description}
                    </p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section 
        className="relative py-24 sm:py-32 bg-gradient-to-br from-purple-50 via-pink-50 to-blue-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900"
        data-section-id="how-it-works"
        ref={setSectionRef('how-it-works')}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className={`text-center mb-12 sm:mb-16 ${visibleSections.has('how-it-works') ? 'animate-fade-in-up' : 'opacity-0'}`}>
            <h2 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold mb-3 sm:mb-4 px-4">
              <span className="gradient-text">How It Works</span>
            </h2>
            <p className="text-lg sm:text-xl text-gray-600 dark:text-gray-400 max-w-2xl mx-auto px-4">
              Get started in minutes, transform your productivity forever
            </p>
          </div>

          <div className="relative">
            {/* Connecting line (hidden on mobile) */}
            <div className="hidden lg:block absolute top-24 left-0 right-0 h-1 bg-gradient-to-r from-purple-500 via-pink-500 to-blue-500 opacity-20 dark:opacity-30"></div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 lg:gap-4">
              {[
                {
                  number: '1',
                  icon: Calendar,
                  title: 'Connect Calendar',
                  description: 'Link your Google Calendar in seconds'
                },
                {
                  number: '2',
                  icon: Sparkles,
                  title: 'AI Extracts Tasks',
                  description: 'Our AI automatically identifies tasks from events'
                },
                {
                  number: '3',
                  icon: Zap,
                  title: 'Set Energy Level',
                  description: 'Tell us how you\'re feeling today'
                },
                {
                  number: '4',
                  icon: Rocket,
                  title: 'Get Your Plan',
                  description: 'Receive your personalized daily plan'
                }
              ].map((step, index) => {
                const Icon = step.icon
                const isVisible = visibleSections.has('how-it-works')
                return (
                  <div
                    key={index}
                    className={`relative ${isVisible ? 'animate-scale-in' : 'opacity-0'}`}
                    style={{ animationDelay: `${index * 150}ms` }}
                  >
                    <div className="text-center">
                      <div className="relative inline-flex items-center justify-center mb-6">
                        <div className="absolute w-24 h-24 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full opacity-20 dark:opacity-30 animate-pulse"></div>
                        <div className="relative w-20 h-20 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full flex items-center justify-center text-white text-3xl font-bold">
                          {step.number}
                        </div>
                        <div className="absolute -top-2 -right-2 w-12 h-12 bg-white dark:bg-gray-800 rounded-full flex items-center justify-center border-2 border-purple-200 dark:border-purple-600">
                          <Icon className="w-6 h-6 text-purple-600 dark:text-purple-400" />
                        </div>
                      </div>
                      <h3 className="text-xl font-bold mb-2 text-gray-900 dark:text-gray-100">
                        {step.title}
                      </h3>
                      <p className="text-gray-600 dark:text-gray-400">
                        {step.description}
                      </p>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section 
        className="relative py-24 sm:py-32 bg-white dark:bg-gray-900"
        data-section-id="benefits"
        ref={setSectionRef('benefits')}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className={`text-center mb-12 sm:mb-16 ${visibleSections.has('benefits') ? 'animate-fade-in-up' : 'opacity-0'}`}>
            <h2 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold mb-3 sm:mb-4 px-4">
              <span className="gradient-text">Why LifeFlow?</span>
            </h2>
            <p className="text-lg sm:text-xl text-gray-600 dark:text-gray-400 max-w-2xl mx-auto px-4">
              Join thousands who've transformed their productivity
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 mb-16">
            {[
              {
                icon: TrendingUp,
                stat: '3x',
                label: 'More Productive',
                description: 'Users report 3x increase in task completion'
              },
              {
                icon: Clock,
                stat: '2hrs',
                label: 'Saved Daily',
                description: 'Average time saved on planning and organization'
              },
              {
                icon: CheckCircle2,
                stat: '95%',
                label: 'Task Completion',
                description: 'Higher completion rate with AI-powered planning'
              }
            ].map((benefit, index) => {
              const Icon = benefit.icon
              const isVisible = visibleSections.has('benefits')
              return (
                <div
                  key={index}
                  className={`text-center p-8 bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-900/30 dark:to-pink-900/30 rounded-2xl border border-purple-100 dark:border-purple-800 transition-all duration-300 hover:scale-105 ${
                    isVisible ? 'animate-scale-in' : 'opacity-0'
                  }`}
                  style={{ animationDelay: `${index * 100}ms` }}
                >
                  <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full mb-4">
                    <Icon className="w-8 h-8 text-white" />
                  </div>
                  <div className="text-5xl font-bold gradient-text mb-2">
                    {benefit.stat}
                  </div>
                  <div className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                    {benefit.label}
                  </div>
                  <p className="text-gray-600 dark:text-gray-400">
                    {benefit.description}
                  </p>
                </div>
              )
            })}
          </div>

          <div className={`grid grid-cols-1 md:grid-cols-2 gap-8 ${visibleSections.has('benefits') ? 'animate-fade-in-up' : 'opacity-0'}`}>
            {[
              'Never miss a deadline again',
              'Focus on what matters most',
              'Reduce stress and overwhelm',
              'Achieve your goals faster',
              'Work smarter, not harder',
              'Get personalized insights'
            ].map((benefit, index) => (
              <div
                key={index}
                className="flex items-center space-x-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-xl hover:bg-gradient-to-r hover:from-purple-50 hover:to-pink-50 dark:hover:from-purple-900/30 dark:hover:to-pink-900/30 transition-all duration-300"
              >
                <CheckCircle2 className="w-6 h-6 text-purple-600 dark:text-purple-400 flex-shrink-0" />
                <span className="text-lg text-gray-900 dark:text-gray-100 font-medium">{benefit}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Target Personas Section */}
      <section 
        className="relative py-24 sm:py-32 bg-gradient-to-b from-white to-gray-50 dark:from-gray-900 dark:to-gray-800"
        data-section-id="personas"
        ref={setSectionRef('personas')}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className={`text-center mb-12 sm:mb-16 ${visibleSections.has('personas') ? 'animate-fade-in-up' : 'opacity-0'}`}>
            <h2 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold mb-3 sm:mb-4 px-4">
              <span className="gradient-text">Built for You</span>
            </h2>
            <p className="text-lg sm:text-xl text-gray-600 dark:text-gray-400 max-w-2xl mx-auto px-4">
              LifeFlow adapts to your unique needs, no matter your role or lifestyle
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 lg:gap-10">
            {[
              {
                icon: Briefcase,
                persona: 'Busy Professionals',
                description: 'Executives, managers, and professionals juggling packed calendars and multiple priorities',
                benefits: [
                  'Automatically extract actionable tasks from meetings and events',
                  'Never miss a deadline with AI-powered priority detection',
                  'Optimize your day based on your energy levels',
                  'Reduce mental overhead with intelligent task organization'
                ],
                gradient: 'from-blue-500 to-cyan-500'
              },
              {
                icon: UserCog,
                persona: 'Entrepreneurs & Freelancers',
                description: 'Self-starters managing multiple clients, projects, and deadlines independently',
                benefits: [
                  'Sync all your client meetings and deadlines in one place',
                  'Get personalized daily plans that maximize productivity',
                  'Track progress across all your projects effortlessly',
                  'Focus on high-impact work with smart priority management'
                ],
                gradient: 'from-purple-500 to-pink-500'
              },
              {
                icon: GraduationCap,
                persona: 'Students',
                description: 'Learners balancing classes, assignments, exams, and extracurricular activities',
                benefits: [
                  'Extract tasks and deadlines from class schedules automatically',
                  'Plan study sessions around your energy and focus levels',
                  'Never forget an assignment with intelligent reminders',
                  'Achieve better work-life balance with optimized scheduling'
                ],
                gradient: 'from-green-500 to-emerald-500'
              },
              {
                icon: HomeIcon,
                persona: 'Remote Workers',
                description: 'Professionals working from home, managing work-life boundaries and multiple priorities',
                benefits: [
                  'Maintain clear boundaries between work and personal time',
                  'Optimize your schedule based on when you work best',
                  'Reduce context switching with intelligent task grouping',
                  'Stay organized without the overwhelm of manual planning'
                ],
                gradient: 'from-orange-500 to-red-500'
              }
            ].map((persona, index) => {
              const Icon = persona.icon
              const isVisible = visibleSections.has('personas')
              return (
                <div
                  key={index}
                  className={`group relative p-8 bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 transition-all duration-300 hover:scale-[1.02] hover:shadow-xl ${
                    isVisible ? 'animate-scale-in' : 'opacity-0'
                  }`}
                  style={{ animationDelay: `${index * 100}ms` }}
                >
                  <div className={`absolute inset-0 bg-gradient-to-br ${persona.gradient} opacity-0 group-hover:opacity-5 dark:group-hover:opacity-10 transition-opacity duration-300 rounded-2xl`}></div>
                  <div className="relative z-10">
                    <div className={`w-16 h-16 bg-gradient-to-br ${persona.gradient} rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300 shadow-lg`}>
                      <Icon className="w-8 h-8 text-white" />
                    </div>
                    <h3 className={`text-2xl font-bold mb-2 text-gray-900 dark:text-gray-100 group-hover:text-transparent group-hover:bg-clip-text group-hover:bg-gradient-to-r ${persona.gradient} transition-all duration-300`}>
                      {persona.persona}
                    </h3>
                    <p className="text-gray-600 dark:text-gray-400 mb-6 leading-relaxed">
                      {persona.description}
                    </p>
                    <div className="space-y-3">
                      {persona.benefits.map((benefit, benefitIndex) => (
                        <div
                          key={benefitIndex}
                          className="flex items-start space-x-3"
                        >
                          <div className={`flex-shrink-0 w-5 h-5 rounded-full bg-gradient-to-br ${persona.gradient} flex items-center justify-center mt-0.5`}>
                            <CheckCircle2 className="w-3 h-3 text-white" />
                          </div>
                          <span className="text-gray-700 dark:text-gray-300 leading-relaxed">{benefit}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section 
        className="relative py-24 sm:py-32 overflow-hidden"
        data-section-id="cta"
        ref={setSectionRef('cta')}
      >
        {/* Animated gradient background */}
        <div className="absolute inset-0 bg-gradient-to-br from-purple-600 via-pink-500 to-blue-500 animate-gradient"></div>
        
        {/* Floating particles */}
        <div className="absolute top-10 left-10 w-16 h-16 bg-white/10 rounded-full blur-xl animate-float"></div>
        <div className="absolute top-32 right-20 w-24 h-24 bg-pink-300/20 rounded-full blur-2xl animate-float-reverse"></div>
        <div className="absolute bottom-20 left-1/3 w-20 h-20 bg-blue-300/20 rounded-full blur-xl animate-float"></div>
        <div className="absolute bottom-32 right-1/4 w-28 h-28 bg-purple-300/20 rounded-full blur-2xl animate-float-reverse"></div>

        <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className={`space-y-6 sm:space-y-8 ${visibleSections.has('cta') ? 'animate-fade-in-up' : 'opacity-0'}`}>
            <h2 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-3 sm:mb-4 px-2">
              Ready to Transform Your Productivity?
            </h2>
            <p className="text-lg sm:text-xl md:text-2xl text-white/90 max-w-2xl mx-auto px-2">
              Join thousands of users who've already transformed their workflow with LifeFlow
            </p>
            <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 justify-center items-center pt-4 px-2">
              <Link
                href="/auth/register"
                className="group relative w-full sm:w-auto px-8 sm:px-10 py-4 sm:py-5 bg-white text-purple-600 font-bold text-lg sm:text-xl rounded-full overflow-hidden transition-all duration-300 hover:scale-110 focus:outline-none focus:ring-4 focus:ring-white/50"
                aria-label="Get started with LifeFlow"
              >
                <span className="relative z-10 flex items-center justify-center gap-2 opacity-100 group-hover:opacity-0 transition-opacity duration-300">
                  Get Started Free
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </span>
                <div className="absolute inset-0 bg-gradient-to-r from-purple-500 to-pink-500 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                <span className="absolute inset-0 flex items-center justify-center gap-2 text-white opacity-0 group-hover:opacity-100 transition-opacity duration-300 z-10">
                  Get Started Free
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </span>
              </Link>
              <Link
                href="/auth/login"
                className="w-full sm:w-auto px-8 sm:px-10 py-4 sm:py-5 border-2 border-white/30 text-white font-bold text-lg sm:text-xl rounded-full backdrop-blur-sm transition-all duration-300 hover:border-white hover:bg-white/10 hover:scale-110 focus:outline-none focus:ring-4 focus:ring-white/50"
                aria-label="Sign in to LifeFlow"
              >
                Sign In
              </Link>
            </div>
            <div className="flex flex-wrap items-center justify-center gap-4 sm:gap-8 pt-6 sm:pt-8 text-white/80 text-sm sm:text-base">
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 sm:w-5 sm:h-5" />
                <span>10K+ Users</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 sm:w-5 sm:h-5" />
                <span>99.9% Uptime</span>
              </div>
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 sm:w-5 sm:h-5" />
                <span>AI-Powered</span>
              </div>
              <a
                href="https://www.linkedin.com/in/lvcarlosja/"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 hover:text-white transition-colors duration-300"
                aria-label="Visit Carlos LinkedIn profile"
              >
                <Linkedin className="w-4 h-4 sm:w-5 sm:h-5" />
                <span>LinkedIn</span>
              </a>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
