import { useLocation, Link } from 'react-router-dom';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Stack from '@mui/material/Stack';
import HomeRoundedIcon from '@mui/icons-material/HomeRounded';
import SettingsRoundedIcon from '@mui/icons-material/SettingsRounded';
import LanguageIcon from '@mui/icons-material/Language';
import ListAltIcon from '@mui/icons-material/ListAlt';
import DashboardIcon from '@mui/icons-material/Dashboard';
import AccountTreeIcon from '@mui/icons-material/AccountTree';

const mainListItems = [
  { text: 'Dashboard', href:"/", icon: <HomeRoundedIcon /> },
  { text: 'TODO List', href:"/todo", icon: <DashboardIcon /> },
  { text: 'Project Explorer', href:"/projects", icon: <AccountTreeIcon /> },
  { text: 'Tasks', href:"/tasks", icon: <ListAltIcon /> },
];

const secondaryListItems = [
  { text: 'Theme Color', icon: <SettingsRoundedIcon /> },
  { text: 'Language', icon: <LanguageIcon /> },
];

export default function MenuContent({ onToggleTheme }: { onToggleTheme: () => void }) {
  const { pathname } = useLocation();
  return (
    <Stack sx={{ flexGrow: 1, p: 1, justifyContent: 'space-between' }}>
      <List>
        {mainListItems.map((item, index) => (
          <ListItem key={index} disablePadding sx={{ display: 'block' }}>
            <ListItemButton selected={item.href === pathname} component={Link} to={item.href}>
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
      <List>
        {secondaryListItems.map((item, index) => (
          <ListItem key={index} disablePadding sx={{ display: 'block' }}>
            <ListItemButton onClick={item.text === 'Theme Color' ? onToggleTheme : undefined}>
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </Stack>
  );
}
