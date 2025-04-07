import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    primary: {
      main: '#1E3A5F',
      light: '#2D5A8E',
      dark: '#0B1D2B',
    },
    secondary: {
      main: '#FFD700',
      light: '#FFE44D',
      dark: '#E6C300',
    },
    background: {
      default: '#0A0F14',
      paper: '#FFFFFF',
    },
    text: {
      primary: '#FFFFFF',
      secondary: '#B8C6D9',
    },
  },
  typography: {
    fontFamily: '"Space Grotesk", "Inter", "Roboto", sans-serif',
    h1: {
      fontFamily: '"Space Grotesk", sans-serif',
      fontSize: '5rem',
      fontWeight: 700,
      letterSpacing: '-0.02em',
      color: '#FFFFFF',
      '@media (max-width:768px)': {
        fontSize: '4rem',
      },
      '@media (max-width:480px)': {
        fontSize: '3rem',
      },
    },
    h2: {
      fontFamily: '"Space Grotesk", sans-serif',
      fontSize: '2rem',
      fontWeight: 600,
      letterSpacing: '-0.01em',
      color: '#FFFFFF',
    },
    h3: {
      fontFamily: '"Inter", sans-serif',
      fontSize: '1.75rem',
      fontWeight: 600,
    },
    body1: {
      fontFamily: '"Inter", sans-serif',
      fontSize: '1rem',
      lineHeight: 1.6,
      color: '#B8C6D9',
    },
    body2: {
      fontFamily: '"Roboto", sans-serif',
      fontSize: '0.875rem',
      lineHeight: 1.5,
    },
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
          padding: '12px 32px',
          borderRadius: '30px',
          fontSize: '1.125rem',
          transition: 'all 0.3s ease-in-out',
          background: 'linear-gradient(45deg, #1E3A5F, #2D5A8E)',
          color: '#FFFFFF',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          backdropFilter: 'blur(10px)',
          '&:hover': {
            transform: 'translateY(-2px)',
            background: 'linear-gradient(45deg, #2D5A8E, #1E3A5F)',
            boxShadow: '0 4px 20px rgba(30, 58, 95, 0.4)',
          },
        },
        contained: {
          boxShadow: 'none',
          '&:hover': {
            boxShadow: '0 4px 20px rgba(30, 58, 95, 0.4)',
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: '12px',
          boxShadow: '0 4px 20px rgba(0,0,0,0.05)',
          transition: 'all 0.3s ease-in-out',
          '&:hover': {
            transform: 'translateY(-4px)',
            boxShadow: '0 8px 30px rgba(0,0,0,0.1)',
          },
        },
      },
    },
  },
});

export default theme; 