import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Box, AppBar, Toolbar, Typography, Container, Grid, CssBaseline } from '@mui/material';
import TaskTable from './components/TaskTable';
import TaskChart from './components/TaskChart';
import CreateTaskForm from './components/createTaskForm';

// REMOVED the hardcoded URL constants.

function App() {
  const [tasks, setTasks] = useState([]);

  const handleRetry = async (taskId) => {
    try {
      // Use a relative path for the API call
      await axios.post(`/api/v1/tasks/${taskId}/retry`);
    } catch (error) {
      console.error(`Failed to retry task ${taskId}:`, error);
      alert(`Failed to retry task ${taskId}. Check the console for details.`);
    }
  };

  useEffect(() => {
    const fetchTasks = async () => {
      try {
        // Use a relative path for the API call
        const response = await axios.get('/api/v1/tasks');
        setTasks(response.data);
      } catch (error) {
        console.error("Failed to fetch tasks:", error);
      }
    };
    fetchTasks();

    // Dynamically create the WebSocket URL from the browser's current location
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsURL = `${protocol}//${window.location.host}/ws`;
    const ws = new WebSocket(wsURL);

    ws.onopen = () => console.log('WebSocket connection established');
    ws.onclose = () => console.log('WebSocket connection closed');
    ws.onerror = (error) => console.error('WebSocket error:', error);

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.event === 'task_update') {
        const updatedTask = message.data;
        setTasks(prevTasks => {
          const taskExists = prevTasks.some(task => task.id === updatedTask.id);
          let newTasks;
          if (taskExists) {
            newTasks = prevTasks.map(task =>
              task.id === updatedTask.id ? updatedTask : task
            );
          } else {
            newTasks = [...prevTasks, updatedTask];
          }
          return newTasks.sort((a, b) => b.id - a.id);
        });
      }
    };

    return () => ws.close();
  }, []); // Note: I fixed a small typo here, changing `,);` to `[]`

  return (
    <Box sx={{ display: 'flex' }}>
      <CssBaseline />
      <AppBar position="fixed">
        <Toolbar>
          <Typography variant="h6" noWrap component="div">
            Orchestra Dashboard
          </Typography>
        </Toolbar>
      </AppBar>
      <Box
        component="main"
        sx={{
          backgroundColor: (theme) =>
            theme.palette.mode === 'light'
              ? theme.palette.grey[100] // Adjusted for a lighter grey
              : theme.palette.grey[900],
          flexGrow: 1,
          height: '100vh',
          overflow: 'auto',
          pt: 8, // Adjust top padding to account for AppBar
        }}
      >
        <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <CreateTaskForm />
            </Grid>
            <Grid item xs={12}>
              <TaskChart tasks={tasks} />
            </Grid>
            <Grid item xs={12}>
              <TaskTable tasks={tasks} onRetry={handleRetry} />
            </Grid>
          </Grid>
        </Container>
      </Box>
    </Box>
  );
}

export default App;