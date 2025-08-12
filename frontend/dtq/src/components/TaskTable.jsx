import React from 'react';
import {
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Chip, Typography, Button
} from '@mui/material';

const statusColors = {
  pending: 'default',
  running: 'info',
  completed: 'success',
  failed: 'error',
  scheduled: 'secondary'
};

const TaskTable = ({ tasks, onRetry }) => {
  return (
    <TableContainer component={Paper}>
      <Typography variant="h6" sx={{ p: 2 }}>Tasks</Typography>
      <Table sx={{ minWidth: 650 }} aria-label="tasks table">
        <TableHead>
          <TableRow>
            <TableCell>ID</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Priority</TableCell>
            <TableCell>Retries</TableCell>
            <TableCell>Payload</TableCell>
            <TableCell>Created At</TableCell>
            <TableCell>Finished At</TableCell>
            <TableCell>Error</TableCell>
            <TableCell>Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {tasks.map((task) => (
            <TableRow key={task.id} sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
              <TableCell component="th" scope="row">{task.id}</TableCell>
              <TableCell>
                <Chip label={task.status} color={statusColors[task.status] || 'default'} size="small" />
              </TableCell>
              <TableCell>{task.priority}</TableCell>
              <TableCell>{task.retry_count}</TableCell>
              <TableCell>{task.payload}</TableCell>
              <TableCell>{new Date(task.created_at).toLocaleString()}</TableCell>
              <TableCell>{task.finished_at? new Date(task.finished_at).toLocaleString() : 'N/A'}</TableCell>
              <TableCell sx={{ color: 'error.main', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {task.error_message}
              </TableCell>
              <TableCell>
                {task.status === 'failed' && (
                  <Button variant="outlined" size="small" onClick={() => onRetry(task.id)}>
                    Retry
                  </Button>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default TaskTable;