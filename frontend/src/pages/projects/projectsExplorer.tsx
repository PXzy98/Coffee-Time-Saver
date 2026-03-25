import { alpha } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

export default function ProjectsExplorer() {
  return (
     <>
      <CssBaseline enableColorScheme />
      <Box sx={{ display: 'flex' }}>

        {/* <AppNavbar /> */}
        {/* Main content */}
        <Box
          component="main"
          sx={(theme) => ({
            flexGrow: 1,
            backgroundColor: theme.vars
              ? `rgba(${theme.vars.palette.background.defaultChannel} / 1)`
              : alpha(theme.palette.background.default, 1),
            overflow: 'auto',
          })}
        >
          <Stack spacing={2} sx={{alignItems: 'center', mx: 3, pb: 5, mt: { xs: 8, md: 0 },}}>
            <Typography component="h2" variant="h6" sx={{ mb: 2 }}>
              Projects
            </Typography>
          </Stack>
        </Box>
      </Box>
    </>
  );
}
