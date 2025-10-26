const express = require('express');
const fileUpload = require('express-fileupload');
const axios = require('axios');
const FormData = require('form-data');
const path = require('path');

const app = express();
const port = 3000;

const PYTHON_SERVICE_URL = 'http://127.0.0.1:5000/analyze';

app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(fileUpload());

app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
});

// *** UPDATED /analyze route ***
app.post('/analyze', async (req, res) => {
  try {
    if (!req.files || !req.files.audio_file) {
      return res.status(400).json({ error: 'No audio file uploaded.' });
    }

    if (!req.body.api_key) {
      return res.status(400).json({ error: 'No API key provided.' });
    }

    const audioFile = req.files.audio_file;
    const apiKey = req.body.api_key;
    
    // *** NEW: Get the audience from the request body ***
    const audience = req.body.audience || ''; // Get audience, or default to empty string

    // Create form data to send to the Python service
    const form = new FormData();
    form.append('api_key', apiKey);
    
    // *** NEW: Add audience to the form data ***
    form.append('audience', audience); 
    
    form.append('audio_file', audioFile.data, {
      filename: audioFile.name,
      contentType: audioFile.mimetype,
    });

    console.log('Sending request to Python service...');
    
    const response = await axios.post(PYTHON_SERVICE_URL, form, {
      headers: form.getHeaders(),
    });

    // The response.data will now contain {"report": "...", "star_rating": 4.5, "time_taken": "..."}
    // We just pass it all straight back to the browser.
    res.json(response.data);

  } catch (error) {
    console.error('Error during analysis:', error);
    if (error.response) {
      res.status(error.response.status).json(error.response.data);
    } else {
      res.status(500).json({ error: 'Internal server error.' });
    }
  }
});

app.listen(port, () => {
  console.log(`Speech analyzer app listening on http://localhost:${port}`);
});