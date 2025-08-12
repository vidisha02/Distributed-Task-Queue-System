import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { ThemeProvider, createTheme } from '@mui/material/styles'; // <-- 1. Import Theme components
import './index.css';
import App from './App.jsx';
import React from 'react';

// 2. Create a default theme instance
const theme = createTheme();

createRoot(document.getElementById('root')).render(
  <StrictMode>
    {/* 3. Wrap your App component in the ThemeProvider */}
    <ThemeProvider theme={theme}>
      <App />
    </ThemeProvider>
  </StrictMode>
);
