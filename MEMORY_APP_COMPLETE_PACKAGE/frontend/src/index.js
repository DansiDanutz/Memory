import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

// Import service worker for PWA functionality
import * as serviceWorkerRegistration from './serviceWorkerRegistration';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// Register service worker for PWA functionality
serviceWorkerRegistration.register();

// Performance monitoring
if (process.env.NODE_ENV === 'development') {
  import('./utils/performance').then(({ reportWebVitals }) => {
    reportWebVitals(console.log);
  });
}

