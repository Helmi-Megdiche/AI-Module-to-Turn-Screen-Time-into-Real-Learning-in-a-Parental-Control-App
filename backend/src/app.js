const express = require('express');
const cors = require('cors');
const morgan = require('morgan');

const routes = require('./routes');

const app = express();

app.use(cors());
// Base64 in JSON is ~33% larger than raw file; JPG screenshots often exceed 1MB → HTML error page if too small
app.use(express.json({ limit: '15mb' }));
app.use(morgan('dev'));

app.use('/api', routes);

module.exports = app;
