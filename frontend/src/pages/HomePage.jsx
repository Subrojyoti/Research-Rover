import React from 'react';
import { Box, Button, Container, Typography } from '@mui/material';
import { TypeAnimation } from 'react-type-animation';
import { styled } from '@mui/material/styles';
import { useNavigate } from 'react-router-dom';

const BackgroundWrapper = styled(Box)({
  position: 'fixed',
  top: 0,
  left: 0,
  width: '100%',
  height: '100%',
  backgroundImage: 'url(/background.jpg)',
  backgroundSize: 'cover',
  backgroundPosition: 'center',
  backgroundAttachment: 'fixed',
  zIndex: -1,
  transition: 'all 0.5s ease-in-out',
  opacity: 1,
});

const ContentWrapper = styled(Container)({
  minHeight: '100vh',
  display: 'flex',
  flexDirection: 'column',
  justifyContent: 'center',
  alignItems: 'center',
  textAlign: 'center',
  position: 'relative',
  zIndex: 1,
  transition: 'all 0.5s ease-in-out',
  opacity: 1,
});

const TitleWrapper = styled(Box)({
  marginBottom: '1rem',
});

const TaglineWrapper = styled(Box)({
  marginBottom: '3rem',
  '& .title-animation': {
    display: 'inline-block',
    overflow: 'hidden',
    whiteSpace: 'nowrap',
  },
});

const HomePage = () => {
  const navigate = useNavigate();

  return (
    <>
      <BackgroundWrapper />
      <ContentWrapper>
        <TitleWrapper>
          <Typography variant="h1">
            Research Rover
          </Typography>
        </TitleWrapper>
        <TaglineWrapper>
          <TypeAnimation
            sequence={['Discover Research Papers Worldwide']}
            wrapper="h2"
            speed={50}
            className="title-animation"
            cursor={true}
            repeat={0}
          />
        </TaglineWrapper>
        <Button
          variant="contained"
          size="large"
          sx={{
            mt: 2,
            px: 4,
            py: 2,
          }}
          onClick={() => navigate('/search')}
        >
          Start your exploration
        </Button>
      </ContentWrapper>
    </>
  );
};

export default HomePage; 