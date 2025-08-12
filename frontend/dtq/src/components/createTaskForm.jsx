import React, { useState } from 'react';
import { Box, Button, TextField, Typography, Select, MenuItem, FormControl, InputLabel, Paper } from '@mui/material';
import axios from 'axios';

const CreateTaskForm = () => {
  const [payload, setPayload] = useState('{"message": "hello world"}');
  const [priority, setPriority] = useState('medium');
  const [delay, setDelay] = useState(0);
  const [feedback, setFeedback] = useState('');
  const [taskType, setTaskType] = useState('io_bound');
  const [isLoading, setIsLoading] = useState(false);

  const handleCreateTask = async () => {
    setIsLoading(true);
    setFeedback('');

    try {
      // Validate that the payload is valid JSON before sending
      JSON.parse(payload);
    } catch (error) {
      setFeedback('Error: Payload must be valid JSON.');
      setIsLoading(false);
      return;
    }

    try {
      // 1. Changed 'type' to 'task_type' to match the backend schema.
      // 2. Removed the hardcoded API_URL to use the Nginx proxy.
      await axios.post('/api/v1/tasks', {
        task_type: taskType,
        payload: payload,
        priority: priority,
        delay: parseInt(delay, 10) || 0,
      });
      setFeedback(`Task created successfully!`);
    } catch (error) {
      const err = error.response?.data || error.message;
      console.error('Backend response:', err);
      // Provide more specific feedback if available from the backend
      const errorMessage = err?.detail?.[0]?.msg || err.detail || 'Failed to create task.';
      setFeedback(`Error: ${errorMessage}`);
    } finally {
      setIsLoading(false);
      setTimeout(() => setFeedback(''), 5000); // Keep feedback visible longer
    }
  };

  return (
    <Paper elevation={3} sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>Create a New Task</Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
            <TextField
                label="Task Payload (JSON)"
                variant="outlined"
                sx={{ flexGrow: 1, minWidth: '200px' }}
                value={payload}
                onChange={(e) => setPayload(e.target.value)}
                multiline
                rows={2}
            />
            <FormControl sx={{ minWidth: 120 }}>
                <InputLabel>Priority</InputLabel>
                <Select
                    value={priority}
                    label="Priority"
                    onChange={(e) => setPriority(e.target.value)}
                >
                    <MenuItem value="high">High</MenuItem>
                    <MenuItem value="medium">Medium</MenuItem>
                    <MenuItem value="low">Low</MenuItem>
                </Select>
            </FormControl>

            <FormControl sx={{ minWidth: 120 }}>
                <InputLabel>Task Type</InputLabel>
                <Select
                    value={taskType}
                    label="Task Type"
                    onChange={(e) => setTaskType(e.target.value)}
                >
                    <MenuItem value="io_bound">I/O Bound</MenuItem>
                    <MenuItem value="cpu_bound">CPU Bound</MenuItem>
                </Select>
            </FormControl>

            <TextField
                label="Delay (sec)"
                type="number"
                value={delay}
                onChange={(e) => setDelay(Math.max(0, parseInt(e.target.value, 10) || 0))}
                sx={{ width: 120 }}
            />
            <Button variant="contained" onClick={handleCreateTask} disabled={isLoading}>
                {isLoading ? 'Creating...' : 'Create Task'}
            </Button>
        </Box>
        {feedback && <Typography sx={{ mt: 2, color: feedback.startsWith('Error:') ? 'error.main' : 'primary.main' }}>{feedback}</Typography>}
    </Paper>
  );
};

export default CreateTaskForm;
