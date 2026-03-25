import Grid from '@mui/material/Grid';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import GridComponent from './GridComponent';


export default function MainGrid() {
  return (
    <Box>
      {/* cards */}
      <Typography component="h2" variant="h6" sx={{ mb: 2 }}>
        Overview
      </Typography>
      <Grid container spacing={2} columns={12} sx={{ mb: (theme) => theme.spacing(2) }}>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <GridComponent />
        </Grid>
        <Grid size={{ xs: 12, md: 6, lg: 3 }}>
          <GridComponent />
        </Grid>
        <Grid size={{ xs: 12, md: 6, lg: 3 }}>
          <GridComponent />
        </Grid>
      </Grid>
      <Typography component="h2" variant="h6" sx={{ mb: 2 }}>
        Details
      </Typography>
      <Grid container spacing={2} columns={12}>
        <Grid size={{ xs: 12, lg: 9 }}>
          <GridComponent />
        </Grid>
      </Grid>
    </Box>
  );
}
