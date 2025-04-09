import React from 'react';
import { Box, Container, Typography, Link, Grid } from '@mui/material';

const Footer = () => {
  return (
    <Box
      component="footer"
      sx={{
        py: 3,
        px: 2,
        mt: 'auto',
        backgroundColor: (theme) => theme.palette.primary.main,
        color: 'white',
        borderTop: '1px solid',
        borderColor: 'divider',
      }}
    >
      <Container maxWidth="lg">
        <Grid container spacing={3} justifyContent="space-between" alignItems="center">
          <Grid item xs={12} sm={6}>
            <Typography variant="body1" align="left" sx={{ fontWeight: 500 }}>
              © {new Date().getFullYear()} Research Rover. All rights reserved.
            </Typography>
          </Grid>
          <Grid item xs={12} sm={6}>
            <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 3 }}>
              <Link href="#" color="inherit" underline="hover" sx={{ fontWeight: 500 }}>
                Privacy Policy
              </Link>
              <Link href="#" color="inherit" underline="hover" sx={{ fontWeight: 500 }}>
                Terms of Service
              </Link>
              <Link href="#" color="inherit" underline="hover" sx={{ fontWeight: 500 }}>
                Contact
              </Link>
            </Box>
          </Grid>
        </Grid>
      </Container>
    </Box>
  );
};

export default Footer; 