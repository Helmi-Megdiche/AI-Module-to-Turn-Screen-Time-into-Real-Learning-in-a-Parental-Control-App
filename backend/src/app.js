const express = require('express');
const cors = require('cors');
const morgan = require('morgan');

const routes = require('./routes');

const app = express();

app.use(cors());
app.use(express.json({ limit: '1mb' }));
app.use(morgan('dev'));

app.use('/api', routes);

module.exports = app;
