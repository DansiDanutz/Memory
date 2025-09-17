import React, { createContext, useContext, useEffect, useState } from 'react';
import { THEMES, STORAGE_KEYS } from '../utils/constants';

const ThemeContext = createContext();

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

export const ThemeProvider = ({ children }) => {
  const [theme, setTheme] = useState(THEMES.SYSTEM);
  const [resolvedTheme, setResolvedTheme] = useState(THEMES.LIGHT);

  // Initialize theme from localStorage or system preference
  useEffect(() => {
    const savedTheme = localStorage.getItem(STORAGE_KEYS.THEME);
    if (savedTheme && Object.values(THEMES).includes(savedTheme)) {
      setTheme(savedTheme);
    } else {
      // Check system preference
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      setTheme(THEMES.SYSTEM);
      setResolvedTheme(prefersDark ? THEMES.DARK : THEMES.LIGHT);
    }
  }, []);

  // Update resolved theme when theme changes
  useEffect(() => {
    let newResolvedTheme;
    
    if (theme === THEMES.SYSTEM) {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      newResolvedTheme = prefersDark ? THEMES.DARK : THEMES.LIGHT;
    } else {
      newResolvedTheme = theme;
    }
    
    setResolvedTheme(newResolvedTheme);
    
    // Apply theme to document
    const root = document.documentElement;
    root.classList.remove(THEMES.LIGHT, THEMES.DARK);
    root.classList.add(newResolvedTheme);
    
    // Update meta theme-color
    const metaThemeColor = document.querySelector('meta[name="theme-color"]');
    if (metaThemeColor) {
      metaThemeColor.setAttribute(
        'content', 
        newResolvedTheme === THEMES.DARK ? '#0D1117' : '#FFFFFF'
      );
    }
    
    // Save to localStorage
    localStorage.setItem(STORAGE_KEYS.THEME, theme);
  }, [theme]);

  // Listen for system theme changes
  useEffect(() => {
    if (theme === THEMES.SYSTEM) {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      
      const handleChange = (e) => {
        setResolvedTheme(e.matches ? THEMES.DARK : THEMES.LIGHT);
      };
      
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }
  }, [theme]);

  const toggleTheme = () => {
    if (resolvedTheme === THEMES.LIGHT) {
      setTheme(THEMES.DARK);
    } else {
      setTheme(THEMES.LIGHT);
    }
  };

  const setThemeMode = (newTheme) => {
    if (Object.values(THEMES).includes(newTheme)) {
      setTheme(newTheme);
    }
  };

  const isDark = resolvedTheme === THEMES.DARK;
  const isLight = resolvedTheme === THEMES.LIGHT;
  const isSystem = theme === THEMES.SYSTEM;

  const value = {
    theme,
    resolvedTheme,
    isDark,
    isLight,
    isSystem,
    toggleTheme,
    setTheme: setThemeMode,
  };

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
};

