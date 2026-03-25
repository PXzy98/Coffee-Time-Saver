import { useTheme } from '@mui/material/styles';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Typography from '@mui/material/Typography';
import Stack from '@mui/material/Stack';


export default function GridComponent() {
  const theme = useTheme();

  const colorPalette = [
    theme.palette.primary.light,
    theme.palette.primary.main,
    theme.palette.primary.dark,
  ];

  return (
    <Card variant="outlined" sx={{ width: '100%' }}>
      <CardContent>
        <Typography component="h1" variant="subtitle1" gutterBottom>
          Demo
        </Typography>
        <Stack sx={{ justifyContent: 'space-between' }}>
          <Stack
            direction="row"
            sx={{
              alignContent: { xs: 'center', sm: 'flex-start' },
              alignItems: 'center',
              gap: 1,
            }}
          >
            <Typography variant="h4" component="p">
              This is our demo component.
            </Typography>
            <Chip size="small" color="success" label="In Progress" />
          </Stack>
          <Typography variant="caption" sx={{ color: 'text.secondary' }}>
            Grid component
          </Typography>
        </Stack>
      </CardContent>
    </Card>
  );
}
